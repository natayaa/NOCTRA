"""Read/write helpers for projects, items, and employees."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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
        stmt = select(Employee).order_by(Employee.name)
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
    ) -> Select:
        from app.modules.projects.constants import TERMINAL_PROJECT_STATUSES

        stmt = select(Project).order_by(Project.created_at.desc())
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
        return stmt

    async def next_code(self) -> str:
        year = datetime.now(UTC).year
        prefix = f"NOCTRA-P-{year}-"
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