"""Analytics service — read-only aggregations across every module.

Every method here runs a bounded set of aggregate queries against
existing tables. No new tables, no materialized views (yet).

Time-basis conventions:
  - Revenue → from `payments` (cash received in the period).
  - COGS    → from `project_items.actual_cost` where the item was created
              in the period.
  - OpEx    → from `expenses` where `expense_date` is in the period.
  - Revenue/Cost by customer → from `projects.approved_price` (or quoted).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, and_, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.constants import (
    Interval,
    pick_interval,
)
from app.modules.analytics.schemas import (
    ActivityEntry,
    CashFlowPoint,
    CustomerValueRow,
    EstimateAccuracyStats,
    FunnelStage,
    InquiryFunnel,
    KpiCard,
    KpiSet,
    MaterialSpendRow,
    ProfitabilityRow,
    SeriesPoint,
    SeriesSet,
)
from app.modules.audit.models import AuditLog
from app.modules.customers.models import Customer
from app.modules.finance.constants import (
    EXPENSE_CATEGORY_LABELS,
    InvoiceStatus,
    PaymentDirection,
)
from app.modules.finance.models import Expense, Invoice, Payment
from app.modules.inquiries.constants import (
    INQUIRY_STATUS_LABELS,
    INQUIRY_STATUSES,
    SERVICE_INTEREST_LABELS,
    InquiryStatus,
)
from app.modules.inquiries.models import Inquiry
from app.modules.inventory.constants import (
    MATERIAL_CATEGORY_LABELS,
    TransactionType,
)
from app.modules.inventory.models import (
    InventoryTransaction,
    Material,
    PurchaseOrder,
)
from app.modules.projects.constants import (
    PROJECT_STATUS_LABELS,
    TERMINAL_PROJECT_STATUSES,
    CostCategory,
    ProjectStatus,
)
from app.modules.projects.models import Project, ProjectItem


def _fmt_rupiah(v: float) -> str:
    n = int(round(v))
    return "Rp " + f"{n:,}".replace(",", ".")


def _fmt_pct(v: float) -> str:
    return f"{v:,.1f}%"


def _fmt_count(v: float) -> str:
    return f"{int(round(v)):,}".replace(",", ".")


def _delta_direction(delta: float) -> str:
    if abs(delta) < 0.01:
        return "flat"
    return "up" if delta > 0 else "down"


def _safe_pct_delta(current: float, previous: float) -> float | None:
    """% change vs previous, or None if no previous baseline."""
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100.0


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ════════════════════════════════════════════════════════════
    # KPI CARDS
    # ════════════════════════════════════════════════════════════

    async def kpis(self, from_date: date, to_date: date) -> KpiSet:
        """Top-of-dashboard KPI cards for the given period."""
        span = (to_date - from_date).days + 1
        prev_to = from_date - timedelta(days=1)
        prev_from = prev_to - timedelta(days=span - 1)

        async def _revenue(f: date, t: date) -> float:
            stmt = (
                select(func.coalesce(func.sum(Payment.amount), 0))
                .where(Payment.direction == PaymentDirection.IN.value)
                .where(Payment.payment_date >= f)
                .where(Payment.payment_date <= t)
            )
            return float((await self.db.execute(stmt)).scalar_one() or 0)

        async def _cogs(f: date, t: date) -> float:
            stmt = (
                select(func.coalesce(func.sum(ProjectItem.actual_cost), 0))
                .where(ProjectItem.actual_cost > 0)
                .where(func.date(ProjectItem.created_at) >= f)
                .where(func.date(ProjectItem.created_at) <= t)
            )
            return float((await self.db.execute(stmt)).scalar_one() or 0)

        async def _opex(f: date, t: date) -> float:
            stmt = (
                select(func.coalesce(func.sum(Expense.amount), 0))
                .where(Expense.expense_date >= f)
                .where(Expense.expense_date <= t)
            )
            return float((await self.db.execute(stmt)).scalar_one() or 0)

        async def _active_projects() -> int:
            stmt = (
                select(func.count(Project.id))
                .where(Project.status.not_in(TERMINAL_PROJECT_STATUSES))
            )
            return int((await self.db.execute(stmt)).scalar_one() or 0)

        async def _pending_inquiries() -> int:
            stmt = (
                select(func.count(Inquiry.id))
                .where(Inquiry.status.in_([
                    InquiryStatus.NEW.value,
                    InquiryStatus.CONTACTED.value,
                    InquiryStatus.QUOTED.value,
                    InquiryStatus.NEGOTIATING.value,
                ]))
            )
            return int((await self.db.execute(stmt)).scalar_one() or 0)

        async def _unpaid_invoices() -> tuple[int, float]:
            stmt = select(Invoice).where(
                Invoice.status.not_in([
                    InvoiceStatus.PAID.value,
                    InvoiceStatus.CANCELLED.value,
                ])
            )
            invoices = (await self.db.execute(stmt)).scalars().all()
            total = 0.0
            for inv in invoices:
                paid_stmt = (
                    select(func.coalesce(func.sum(Payment.amount), 0))
                    .where(Payment.reference_type == "INVOICE")
                    .where(Payment.reference_id == inv.id)
                    .where(Payment.direction == PaymentDirection.IN.value)
                )
                paid = float((await self.db.execute(paid_stmt)).scalar_one() or 0)
                total += max(0, float(inv.total) - paid)
            return len(invoices), total

        async def _low_stock() -> int:
            """Materials whose current stock is below reorder point."""
            from app.modules.inventory.constants import (
                INBOUND_TYPES,
            )
            # Aggregate per material
            stock_stmt = (
                select(
                    InventoryTransaction.material_id,
                    func.coalesce(func.sum(
                        case(
                            (
                                InventoryTransaction.transaction_type.in_(
                                    ["OPENING", "PURCHASE", "ADJUSTMENT_IN", "TRANSFER_IN"]
                                ),
                                InventoryTransaction.quantity,
                            ),
                            else_=-InventoryTransaction.quantity,
                        )
                    ), 0).label("stock"),
                )
                .group_by(InventoryTransaction.material_id)
            )
            rows = (await self.db.execute(stock_stmt)).all()
            stock_map = {r.material_id: float(r.stock) for r in rows}

            mat_stmt = select(Material).where(Material.is_active.is_(True))
            materials = (await self.db.execute(mat_stmt)).scalars().all()
            count = 0
            for m in materials:
                if float(m.reorder_point) <= 0:
                    continue
                stock = stock_map.get(m.id, 0.0)
                if stock <= float(m.reorder_point):
                    count += 1
            return count

        # ── Compute everything ──────────────────────────────
        rev_cur = await _revenue(from_date, to_date)
        rev_prev = await _revenue(prev_from, prev_to)
        cogs_cur = await _cogs(from_date, to_date)
        cogs_prev = await _cogs(prev_from, prev_to)
        opex_cur = await _opex(from_date, to_date)
        opex_prev = await _opex(prev_from, prev_to)

        gross_cur = rev_cur - cogs_cur
        gross_prev = rev_prev - cogs_prev
        net_cur = gross_cur - opex_cur
        net_prev = gross_prev - opex_prev

        margin_cur = (gross_cur / rev_cur * 100) if rev_cur else 0.0
        margin_prev = (gross_prev / rev_prev * 100) if rev_prev else 0.0

        active_projects = await _active_projects()
        pending_inquiries = await _pending_inquiries()
        unpaid_count, unpaid_total = await _unpaid_invoices()
        low_stock = await _low_stock()

        def _delta_pair(cur: float, prev: float) -> tuple[float | None, str | None]:
            d = _safe_pct_delta(cur, prev)
            return d, (_delta_direction(d) if d is not None else None)

        rev_d, rev_dir = _delta_pair(rev_cur, rev_prev)
        gross_d, gross_dir = _delta_pair(gross_cur, gross_prev)
        net_d, net_dir = _delta_pair(net_cur, net_prev)
        margin_d = (margin_cur - margin_prev) if rev_prev else None
        margin_dir = _delta_direction(margin_d) if margin_d is not None else None

        cards = [
            KpiCard(
                key="revenue", label="Revenue", value=rev_cur,
                formatted=_fmt_rupiah(rev_cur),
                delta_pct=round(rev_d, 1) if rev_d is not None else None,
                delta_direction=rev_dir,
                hint="Cash received in period",
            ),
            KpiCard(
                key="gross_profit", label="Gross profit", value=gross_cur,
                formatted=_fmt_rupiah(gross_cur),
                delta_pct=round(gross_d, 1) if gross_d is not None else None,
                delta_direction=gross_dir,
                hint=f"{_fmt_pct(margin_cur)} margin",
            ),
            KpiCard(
                key="net_profit", label="Net profit", value=net_cur,
                formatted=_fmt_rupiah(net_cur),
                delta_pct=round(net_d, 1) if net_d is not None else None,
                delta_direction=net_dir,
                hint="Revenue − COGS − OpEx",
            ),
            KpiCard(
                key="gross_margin", label="Gross margin", value=margin_cur,
                formatted=_fmt_pct(margin_cur),
                delta_pct=round(margin_d, 2) if margin_d is not None else None,
                delta_direction=margin_dir,
                hint="vs previous period",
            ),
            KpiCard(
                key="active_projects", label="Active projects",
                value=float(active_projects),
                formatted=_fmt_count(active_projects),
                hint="Not yet delivered or cancelled",
            ),
            KpiCard(
                key="pending_inquiries", label="Open inquiries",
                value=float(pending_inquiries),
                formatted=_fmt_count(pending_inquiries),
                hint="New through negotiating",
            ),
            KpiCard(
                key="unpaid_invoices", label="Unpaid invoices",
                value=unpaid_total,
                formatted=_fmt_rupiah(unpaid_total),
                hint=f"{unpaid_count} invoice{'s' if unpaid_count != 1 else ''}",
            ),
            KpiCard(
                key="low_stock", label="Low stock alerts",
                value=float(low_stock),
                formatted=_fmt_count(low_stock),
                hint="At or below reorder point",
            ),
        ]

        return KpiSet(period_from=from_date, period_to=to_date, cards=cards)

    # ════════════════════════════════════════════════════════════
    # TIME SERIES
    # ════════════════════════════════════════════════════════════

    async def revenue_series(
        self, from_date: date, to_date: date, interval: str | None = None
    ) -> SeriesSet:
        interval = interval or pick_interval(from_date, to_date)
        bucket = func.date_trunc(interval, Payment.payment_date).label("period")

        stmt = (
            select(bucket, func.coalesce(func.sum(Payment.amount), 0).label("total"))
            .where(Payment.direction == PaymentDirection.IN.value)
            .where(Payment.payment_date >= from_date)
            .where(Payment.payment_date <= to_date)
            .group_by(bucket)
            .order_by(bucket)
        )
        rows = (await self.db.execute(stmt)).all()
        points = [
            SeriesPoint(period=r.period.date() if hasattr(r.period, "date") else r.period,
                        value=float(r.total or 0))
            for r in rows
        ]
        return SeriesSet(label="Revenue", interval=interval, points=points)

    async def expense_series(
        self, from_date: date, to_date: date, interval: str | None = None
    ) -> SeriesSet:
        interval = interval or pick_interval(from_date, to_date)
        bucket = func.date_trunc(interval, Expense.expense_date).label("period")

        stmt = (
            select(bucket, func.coalesce(func.sum(Expense.amount), 0).label("total"))
            .where(Expense.expense_date >= from_date)
            .where(Expense.expense_date <= to_date)
            .group_by(bucket)
            .order_by(bucket)
        )
        rows = (await self.db.execute(stmt)).all()
        points = [
            SeriesPoint(period=r.period.date() if hasattr(r.period, "date") else r.period,
                        value=float(r.total or 0))
            for r in rows
        ]
        return SeriesSet(label="Expenses", interval=interval, points=points)

    async def cash_flow_series(
        self, from_date: date, to_date: date, interval: str | None = None
    ) -> list[CashFlowPoint]:
        interval = interval or pick_interval(from_date, to_date)
        bucket = func.date_trunc(interval, Payment.payment_date).label("period")

        stmt = (
            select(
                bucket,
                Payment.direction,
                func.coalesce(func.sum(Payment.amount), 0).label("total"),
            )
            .where(Payment.payment_date >= from_date)
            .where(Payment.payment_date <= to_date)
            .group_by(bucket, Payment.direction)
            .order_by(bucket)
        )
        rows = (await self.db.execute(stmt)).all()

        # Aggregate into a dict keyed by period
        merged: dict[date, dict[str, float]] = {}
        for r in rows:
            period = r.period.date() if hasattr(r.period, "date") else r.period
            slot = merged.setdefault(period, {"inflow": 0.0, "outflow": 0.0})
            if r.direction == PaymentDirection.IN.value:
                slot["inflow"] += float(r.total or 0)
            else:
                slot["outflow"] += float(r.total or 0)

        return [
            CashFlowPoint(
                period=p,
                inflow=v["inflow"],
                outflow=v["outflow"],
                net=v["inflow"] - v["outflow"],
            )
            for p, v in sorted(merged.items())
        ]

    async def gross_profit_series(
        self, from_date: date, to_date: date, interval: str | None = None
    ) -> SeriesSet:
        """Revenue − COGS, per period."""
        interval = interval or pick_interval(from_date, to_date)

        rev = await self.revenue_series(from_date, to_date, interval)

        cogs_bucket = func.date_trunc(interval, ProjectItem.created_at).label("period")
        cogs_stmt = (
            select(cogs_bucket, func.coalesce(func.sum(ProjectItem.actual_cost), 0).label("total"))
            .where(ProjectItem.actual_cost > 0)
            .where(func.date(ProjectItem.created_at) >= from_date)
            .where(func.date(ProjectItem.created_at) <= to_date)
            .group_by(cogs_bucket)
            .order_by(cogs_bucket)
        )
        cogs_rows = (await self.db.execute(cogs_stmt)).all()
        cogs_by_period: dict[date, float] = {
            (r.period.date() if hasattr(r.period, "date") else r.period): float(r.total or 0)
            for r in cogs_rows
        }

        points = []
        for p in rev.points:
            points.append(
                SeriesPoint(
                    period=p.period,
                    value=p.value - cogs_by_period.get(p.period, 0.0),
                )
            )
        return SeriesSet(label="Gross profit", interval=interval, points=points)

    # ════════════════════════════════════════════════════════════
    # PROFITABILITY BY SEGMENT
    # ════════════════════════════════════════════════════════════

    async def service_profitability(
        self, from_date: date, to_date: date
    ) -> list[ProfitabilityRow]:
        """
        Revenue and cost grouped by inquiry.service_interest.
        Projects without an inquiry link are grouped under UNKNOWN.
        """
        stmt = (
            select(
                Inquiry.service_interest,
                func.count(Project.id).label("project_count"),
                func.coalesce(func.sum(
                    func.coalesce(Project.approved_price, Project.quoted_price, 0)
                ), 0).label("revenue"),
                func.coalesce(func.sum(Project.actual_hpp), 0).label("cogs"),
            )
            .select_from(Project)
            .outerjoin(Inquiry, Inquiry.id == Project.inquiry_id)
            .where(func.date(Project.created_at) >= from_date)
            .where(func.date(Project.created_at) <= to_date)
            .group_by(Inquiry.service_interest)
            .order_by(func.sum(Project.actual_hpp).desc())
        )
        rows = (await self.db.execute(stmt)).all()

        result: list[ProfitabilityRow] = []
        for r in rows:
            key = r.service_interest or "UNKNOWN"
            label = SERVICE_INTEREST_LABELS.get(key, key.title())
            revenue = float(r.revenue or 0)
            cogs = float(r.cogs or 0)
            gp = revenue - cogs
            margin_pct = (gp / revenue * 100) if revenue > 0 else 0.0
            count = int(r.project_count or 0)
            result.append(
                ProfitabilityRow(
                    key=key,
                    label=label,
                    project_count=count,
                    revenue=revenue,
                    cogs=cogs,
                    gross_profit=gp,
                    gross_margin_pct=round(margin_pct, 2),
                    avg_project_value=round(revenue / count, 2) if count else 0.0,
                )
            )
        return result

    async def vehicle_category_profitability(
        self, from_date: date, to_date: date
    ) -> list[ProfitabilityRow]:
        from app.modules.vehicles.models import Vehicle

        stmt = (
            select(
                Vehicle.category,
                func.count(Project.id).label("project_count"),
                func.coalesce(func.sum(
                    func.coalesce(Project.approved_price, Project.quoted_price, 0)
                ), 0).label("revenue"),
                func.coalesce(func.sum(Project.actual_hpp), 0).label("cogs"),
            )
            .select_from(Project)
            .outerjoin(Vehicle, Vehicle.id == Project.vehicle_id)
            .where(func.date(Project.created_at) >= from_date)
            .where(func.date(Project.created_at) <= to_date)
            .group_by(Vehicle.category)
            .order_by(func.sum(Project.actual_hpp).desc())
        )
        rows = (await self.db.execute(stmt)).all()

        result: list[ProfitabilityRow] = []
        for r in rows:
            key = r.category or "UNKNOWN"
            revenue = float(r.revenue or 0)
            cogs = float(r.cogs or 0)
            gp = revenue - cogs
            margin_pct = (gp / revenue * 100) if revenue > 0 else 0.0
            count = int(r.project_count or 0)
            result.append(
                ProfitabilityRow(
                    key=key,
                    label=key.replace("_", " ").title(),
                    project_count=count,
                    revenue=revenue,
                    cogs=cogs,
                    gross_profit=gp,
                    gross_margin_pct=round(margin_pct, 2),
                    avg_project_value=round(revenue / count, 2) if count else 0.0,
                )
            )
        return result

    # ════════════════════════════════════════════════════════════
    # CUSTOMER VALUE
    # ════════════════════════════════════════════════════════════

    async def top_customers(
        self, from_date: date, to_date: date, limit: int = 10
    ) -> list[CustomerValueRow]:
        stmt = (
            select(
                Customer.id,
                Customer.code,
                Customer.name,
                func.count(Project.id).label("project_count"),
                func.coalesce(func.sum(
                    func.coalesce(Project.approved_price, Project.quoted_price, 0)
                ), 0).label("revenue"),
                func.coalesce(func.sum(Project.actual_hpp), 0).label("cost"),
                func.max(Project.created_at).label("last_project"),
            )
            .select_from(Customer)
            .join(Project, Project.customer_id == Customer.id)
            .where(func.date(Project.created_at) >= from_date)
            .where(func.date(Project.created_at) <= to_date)
            .group_by(Customer.id, Customer.code, Customer.name)
            .order_by(func.sum(
                func.coalesce(Project.approved_price, Project.quoted_price, 0)
            ).desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        result: list[CustomerValueRow] = []
        for r in rows:
            revenue = float(r.revenue or 0)
            cost = float(r.cost or 0)
            gp = revenue - cost
            margin_pct = (gp / revenue * 100) if revenue > 0 else 0.0
            last = r.last_project
            if last and hasattr(last, "date"):
                last = last.date()
            result.append(
                CustomerValueRow(
                    customer_id=r.id,
                    code=r.code,
                    name=r.name,
                    project_count=int(r.project_count or 0),
                    total_revenue=revenue,
                    total_cost=cost,
                    gross_profit=gp,
                    margin_pct=round(margin_pct, 2),
                    last_project_date=last,
                )
            )
        return result

    # ════════════════════════════════════════════════════════════
    # MATERIAL SPEND
    # ════════════════════════════════════════════════════════════

    async def top_materials(
        self, from_date: date, to_date: date, limit: int = 20
    ) -> list[MaterialSpendRow]:
        stmt = (
            select(
                Material.id,
                Material.code,
                Material.name,
                Material.category,
                Material.stock_unit,
                func.coalesce(func.sum(InventoryTransaction.quantity), 0).label("consumed"),
                func.coalesce(func.sum(
                    InventoryTransaction.quantity * InventoryTransaction.unit_cost
                ), 0).label("cost"),
            )
            .select_from(InventoryTransaction)
            .join(Material, Material.id == InventoryTransaction.material_id)
            .where(InventoryTransaction.transaction_type == TransactionType.CONSUMPTION.value)
            .where(func.date(InventoryTransaction.created_at) >= from_date)
            .where(func.date(InventoryTransaction.created_at) <= to_date)
            .group_by(Material.id, Material.code, Material.name, Material.category, Material.stock_unit)
            .order_by(func.sum(
                InventoryTransaction.quantity * InventoryTransaction.unit_cost
            ).desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            MaterialSpendRow(
                material_id=r.id,
                code=r.code,
                name=r.name,
                category=r.category,
                unit=r.stock_unit,
                total_consumed=float(r.consumed or 0),
                total_cost=float(r.cost or 0),
            )
            for r in rows
        ]

    # ════════════════════════════════════════════════════════════
    # ESTIMATE ACCURACY
    # ════════════════════════════════════════════════════════════

    async def estimate_accuracy(
        self, from_date: date, to_date: date
    ) -> EstimateAccuracyStats:
        """
        Compare estimated_hpp vs actual_hpp for projects in the period.
        Only projects with both non-zero.
        """
        stmt = (
            select(Project.estimated_hpp, Project.actual_hpp)
            .where(Project.estimated_hpp > 0)
            .where(Project.actual_hpp > 0)
            .where(func.date(Project.created_at) >= from_date)
            .where(func.date(Project.created_at) <= to_date)
        )
        rows = (await self.db.execute(stmt)).all()

        if not rows:
            return EstimateAccuracyStats(
                project_count=0,
                avg_variance_pct=0.0,
                median_variance_pct=0.0,
                worst_overrun_pct=0.0,
                best_case_pct=0.0,
                avg_estimated_hpp=0.0,
                avg_actual_hpp=0.0,
            )

        # variance = (actual − estimated) / estimated × 100
        # positive = overrun, negative = under
        variances: list[float] = []
        est_sum = act_sum = 0.0
        for r in rows:
            est = float(r.estimated_hpp)
            act = float(r.actual_hpp)
            variances.append(((act - est) / est) * 100.0)
            est_sum += est
            act_sum += act

        variances.sort()
        n = len(variances)
        median = variances[n // 2] if n % 2 == 1 else (variances[n // 2 - 1] + variances[n // 2]) / 2.0

        return EstimateAccuracyStats(
            project_count=n,
            avg_variance_pct=round(sum(variances) / n, 2),
            median_variance_pct=round(median, 2),
            worst_overrun_pct=round(max(variances), 2),
            best_case_pct=round(min(variances), 2),
            avg_estimated_hpp=round(est_sum / n, 2),
            avg_actual_hpp=round(act_sum / n, 2),
        )

    # ════════════════════════════════════════════════════════════
    # INQUIRY FUNNEL
    # ════════════════════════════════════════════════════════════

    async def inquiry_funnel(self, from_date: date, to_date: date) -> InquiryFunnel:
        stmt = (
            select(Inquiry.status, func.count(Inquiry.id))
            .where(func.date(Inquiry.created_at) >= from_date)
            .where(func.date(Inquiry.created_at) <= to_date)
            .group_by(Inquiry.status)
        )
        rows = (await self.db.execute(stmt)).all()
        counts = {r[0]: int(r[1]) for r in rows}
        total = sum(counts.values())

        stages = []
        for status in INQUIRY_STATUSES:
            count = counts.get(status, 0)
            pct = (count / total * 100) if total else 0.0
            stages.append(
                FunnelStage(
                    status=status,
                    label=INQUIRY_STATUS_LABELS.get(status, status),
                    count=count,
                    pct_of_total=round(pct, 1),
                )
            )

        return InquiryFunnel(total=total, stages=stages)

    # ════════════════════════════════════════════════════════════
    # RECENT ACTIVITY
    # ════════════════════════════════════════════════════════════

    async def recent_activity(self, limit: int = 20) -> list[ActivityEntry]:
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [
            ActivityEntry(
                id=r.id,
                action=r.action,
                table_name=r.table_name,
                record_id=r.record_id,
                user_id=r.user_id,
                created_at=r.created_at,
            )
            for r in rows
        ]