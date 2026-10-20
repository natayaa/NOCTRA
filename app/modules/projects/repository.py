"""Read/write helpers for projects, items, and employees."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.modules.projects.constants import TERMINAL_PROJECT_STATUSES
from app.modules.projects.models import Employee, Project, ProjectItem


class EmployeeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, eid: UUID) -> Employee | None:
        return await self.db.get(Employee, eid)

    async def by_code(self, code: str) -> Employee | None:
        stmt = select(Employee).where(Employee.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
    ) -> Select:
        # Stable secondary sort prevents pagination drift on name ties.
        stmt = select(Employee).order_by(Employee.name.asc(), Employee.id.asc())
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Employee.name.ilike(like),
                    Employee.code.ilike(like),
                    Employee.position.ilike(like),
                )
            )
        if is_active is not None:
            conds.append(Employee.is_active == is_active)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def next_code(self) -> str:
        """
        Generate EMP-NNN under an advisory lock. Serialises concurrent
        creation so the unique constraint cannot collide.
        """
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": "employee-code"},
        )
        stmt = (
            select(Employee.code)
            .where(Employee.code.like("EMP-%"))
            .order_by(Employee.code.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalar_one_or_none()
        n = 1 if last is None else int(last.rsplit("-", 1)[-1]) + 1
        return f"EMP-{n:03d}"

    async def add(self, emp: Employee) -> Employee:
        self.db.add(emp)
        await self.db.flush()
        return emp


class ProjectRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, pid: UUID) -> Project | None:
        return await self.db.get(Project, pid)

    async def get_for_update(self, pid: UUID) -> Project | None:
        """Load with row-level lock; prevents concurrent status transitions."""
        stmt = (
            select(Project)
            .where(Project.id == pid)
            .with_for_update()
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_code(self, code: str) -> Project | None:
        stmt = select(Project).where(Project.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        customer_id: UUID | None = None,
        vehicle_id: UUID | None = None,
        assigned_lead_id: UUID | None = None,
        only_open: bool = False,
        sort: str = "created_desc",
    ) -> Select:
        # `noload` prevents selectin eager loading of `items` in list views.
        stmt = select(Project).options(noload(Project.items))
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Project.code.ilike(like),
                    Project.title.ilike(like),
                    Project.description.ilike(like),
                )
            )
        if status:
            conds.append(Project.status == status)
        if customer_id:
            conds.append(Project.customer_id == customer_id)
        if vehicle_id:
            conds.append(Project.vehicle_id == vehicle_id)
        if assigned_lead_id:
            conds.append(Project.assigned_lead_id == assigned_lead_id)
        if only_open:
            conds.append(Project.status.not_in(TERMINAL_PROJECT_STATUSES))
        if conds:
            stmt = stmt.where(and_(*conds))

        # Stable secondary sort on id for pagination.
        if sort == "created_asc":
            stmt = stmt.order_by(Project.created_at.asc(), Project.id.asc())
        elif sort == "updated_desc":
            stmt = stmt.order_by(Project.updated_at.desc(), Project.id.asc())
        elif sort == "target_asc":
            stmt = stmt.order_by(
                Project.target_end_date.asc().nulls_last(), Project.id.asc()
            )
        elif sort == "priority_desc":
            stmt = stmt.order_by(
                Project.priority.desc(), Project.created_at.desc(), Project.id.asc()
            )
        else:
            stmt = stmt.order_by(Project.created_at.desc(), Project.id.asc())

        return stmt

    async def stats(self, *, customer_id: UUID | None = None) -> dict[str, int | float]:
        """Aggregate counts per status + open/total financials."""
        base = select(Project.status, func.count(Project.id)).group_by(Project.status)
        if customer_id:
            base = base.where(Project.customer_id == customer_id)
        rows = (await self.db.execute(base)).all()
        by_status = {s: c for s, c in rows}

        open_stmt = select(func.count(Project.id)).where(
            Project.status.not_in(TERMINAL_PROJECT_STATUSES)
        )
        if customer_id:
            open_stmt = open_stmt.where(Project.customer_id == customer_id)
        open_count = (await self.db.execute(open_stmt)).scalar_one()

        totals_stmt = select(
            func.coalesce(func.sum(Project.estimated_hpp), 0),
            func.coalesce(func.sum(Project.actual_hpp), 0),
            func.coalesce(func.sum(Project.approved_price), 0),
        )
        if customer_id:
            totals_stmt = totals_stmt.where(Project.customer_id == customer_id)
        est, act, approved = (await self.db.execute(totals_stmt)).one()

        return {
            "total": sum(by_status.values()),
            "open": open_count,
            "estimated_hpp_total": float(est),
            "actual_hpp_total": float(act),
            "approved_price_total": float(approved),
            **{f"status_{k}": v for k, v in by_status.items()},
        }

    async def next_code(self) -> str:
        """
        Generate NOCTRA-P-YYYY-NNNNNN under an advisory lock. Serialises
        concurrent creation so the unique constraint cannot collide.
        """
        year = datetime.now(UTC).year
        prefix = f"NOCTRA-P-{year}-"

        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": prefix},
        )

        stmt = (
            select(Project.code)
            .where(Project.code.like(f"{prefix}%"))
            .order_by(Project.code.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalar_one_or_none()
        n = 1 if last is None else int(last.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{n:06d}"

    async def add(self, project: Project) -> Project:
        self.db.add(project)
        await self.db.flush()
        return project

    # ── Items ──────────────────────────────────────────

    async def get_item(self, item_id: UUID) -> ProjectItem | None:
        return await self.db.get(ProjectItem, item_id)

    async def list_items(self, project_id: UUID) -> list[ProjectItem]:
        stmt = (
            select(ProjectItem)
            .where(ProjectItem.project_id == project_id)
            .order_by(ProjectItem.created_at)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def add_item(self, item: ProjectItem) -> ProjectItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def delete_item(self, item: ProjectItem) -> None:
        await self.db.delete(item)
        await self.db.flush()