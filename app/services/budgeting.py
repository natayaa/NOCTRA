# services/budgeting.py
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, desc

from models.projects import Project
from models.customer_inquiry import CustomerInquiry
from models.expenses import Expense
from models.inventory_items import InventoryItems
from models.inventory_material_usage import JobMaterialUsage

from schemas.expenses import ExpenseCreate, ExpenseUpdate
from schemas.budgeting import (
    SummaryResponse, KPIsResponse,
    MonthlyExpensePoint, BreakdownItem,
    CashflowPoint, ProjectProfitabilityItem
)


class BudgetingService:
    """
    Service for budgeting & financial management.
    Aggregates data from Projects, Expenses, and Inventory.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Helper: Period Range
    # -------------------------------------------------------------------------

    def _get_period_range(self, period: str) -> tuple[date, date]:
        """Return start and end date for a given period."""
        today = date.today()
        if period == 'month':
            start = today.replace(day=1)
            end = today
        elif period == 'last_month':
            first = today.replace(day=1) - timedelta(days=1)
            start = first.replace(day=1)
            end = first
        elif period == 'quarter':
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start = today.replace(month=quarter_month, day=1)
            end = today
        elif period == 'year':
            start = today.replace(month=1, day=1)
            end = today
        else:
            start = today - timedelta(days=30)
            end = today
        return start, end

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    async def get_summary(self, period: str) -> SummaryResponse:
        """Return summary cards data."""
        start, end = self._get_period_range(period)

        # Active projects (status in progress)
        active_projects = await self.db.scalar(
            select(func.count(Project.id)).where(
                Project.status.in_(['preparation', 'painting', 'assembly'])
            )
        ) or 0

        # Pending payments = total actual_revenue - actual_cost for completed projects not fully paid?
        # We'll use total actual_revenue for completed projects.
        pending = await self.db.scalar(
            select(func.sum(Project.actual_revenue - Project.actual_cost))
            .where(Project.status == 'completed')
        ) or Decimal(0)

        # Material cost ratio = total material expenses / total revenue
        # Material expenses from Expense with category 'Material'
        material_expenses = await self.db.scalar(
            select(func.sum(Expense.amount))
            .where(
                Expense.category == 'Material',
                Expense.expense_date >= start,
                Expense.expense_date <= end
            )
        ) or Decimal(0)

        total_revenue = await self.db.scalar(
            select(func.sum(Project.actual_revenue))
            .where(Project.status == 'completed')
        ) or Decimal(1)  # avoid division by zero

        material_ratio = float((material_expenses / total_revenue) * 100) if total_revenue else 0

        # Average project profit
        avg_profit = await self.db.scalar(
            select(func.avg(Project.actual_revenue - Project.actual_cost))
            .where(Project.status == 'completed')
        ) or Decimal(0)

        return SummaryResponse(
            active_projects=active_projects,
            pending_payments=pending,
            material_cost_ratio=round(material_ratio, 1),
            avg_project_profit=avg_profit
        )

    # -------------------------------------------------------------------------
    # KPIs
    # -------------------------------------------------------------------------

    async def get_kpis(self, period: str) -> KPIsResponse:
        """Return main KPIs: revenue, expenses, net profit, cash available."""
        start, end = self._get_period_range(period)

        # Revenue from projects completed in period
        revenue = await self.db.scalar(
            select(func.sum(Project.actual_revenue))
            .where(
                Project.status == 'completed',
                Project.completed_at >= start,
                Project.completed_at <= end
            )
        ) or Decimal(0)

        # Expenses from Expense table in period
        expenses = await self.db.scalar(
            select(func.sum(Expense.amount))
            .where(
                Expense.expense_date >= start,
                Expense.expense_date <= end
            )
        ) or Decimal(0)

        net_profit = revenue - expenses

        # Cash available = total revenue all time - total expenses all time
        total_revenue = await self.db.scalar(
            select(func.sum(Project.actual_revenue))
        ) or Decimal(0)
        total_expenses = await self.db.scalar(
            select(func.sum(Expense.amount))
        ) or Decimal(0)
        cash_available = total_revenue - total_expenses

        return KPIsResponse(
            revenue=revenue,
            expenses=expenses,
            net_profit=net_profit,
            cash_available=cash_available
        )

    # -------------------------------------------------------------------------
    # Charts
    # -------------------------------------------------------------------------

    async def get_monthly_expenses(self, period: str) -> List[MonthlyExpensePoint]:
        """Return monthly expenses for line chart."""
        start, end = self._get_period_range(period)

        # Group by month within period
        # For simplicity, we'll get last 6 months from period end
        if period == 'month':
            months = 6
        elif period == 'quarter':
            months = 3
        else:
            months = 12

        # Get monthly sums
        stmt = select(
            func.date_trunc('month', Expense.expense_date).label('month'),
            func.sum(Expense.amount).label('total')
        ).where(
            Expense.expense_date >= start,
            Expense.expense_date <= end
        ).group_by('month').order_by('month')

        result = await self.db.execute(stmt)
        rows = result.all()

        # Build label: 'Jan 2026'
        data = []
        for row in rows:
            month = row.month.strftime('%b %Y')
            data.append(MonthlyExpensePoint(month=month, amount=row.total or Decimal(0)))

        return data

    async def get_expense_breakdown(self, period: str) -> List[BreakdownItem]:
        """Return expense breakdown by category for pie chart."""
        start, end = self._get_period_range(period)

        stmt = select(
            Expense.category,
            func.sum(Expense.amount).label('total')
        ).where(
            Expense.expense_date >= start,
            Expense.expense_date <= end
        ).group_by(Expense.category)

        result = await self.db.execute(stmt)
        rows = result.all()

        total = sum(row.total for row in rows) or Decimal(1)
        items = []
        for row in rows:
            pct = float((row.total / total) * 100)
            items.append(BreakdownItem(
                category=row.category,
                amount=row.total,
                percentage=round(pct, 1)
            ))
        return items

    async def get_cashflow(self, period: str) -> List[CashflowPoint]:
        """Return revenue vs expenses per month for bar chart."""
        start, end = self._get_period_range(period)

        # Revenue per month from projects
        rev_stmt = select(
            func.date_trunc('month', Project.completed_at).label('month'),
            func.sum(Project.actual_revenue).label('revenue')
        ).where(
            Project.status == 'completed',
            Project.completed_at >= start,
            Project.completed_at <= end
        ).group_by('month').order_by('month')

        # Expenses per month from Expense
        exp_stmt = select(
            func.date_trunc('month', Expense.expense_date).label('month'),
            func.sum(Expense.amount).label('expenses')
        ).where(
            Expense.expense_date >= start,
            Expense.expense_date <= end
        ).group_by('month').order_by('month')

        rev_result = await self.db.execute(rev_stmt)
        exp_result = await self.db.execute(exp_stmt)

        # Merge into dict
        rev_dict = {row.month.strftime('%b %Y'): row.revenue for row in rev_result}
        exp_dict = {row.month.strftime('%b %Y'): row.expenses for row in exp_result}

        all_months = sorted(set(rev_dict.keys()) | set(exp_dict.keys()))
        data = []
        for m in all_months:
            data.append(CashflowPoint(
                month=m,
                revenue=rev_dict.get(m, Decimal(0)),
                expenses=exp_dict.get(m, Decimal(0))
            ))
        return data

    # -------------------------------------------------------------------------
    # Project Profitability
    # -------------------------------------------------------------------------

    async def get_project_profitability(self) -> List[ProjectProfitabilityItem]:
        """Return profitability for each completed project."""
        stmt = select(Project).where(
            Project.status == 'completed'
        ).order_by(desc(Project.actual_revenue))

        result = await self.db.execute(stmt)
        projects = result.scalars().all()

        items = []
        for p in projects:
            revenue = p.actual_revenue or Decimal(0)
            cost = p.actual_cost or Decimal(0)
            profit = revenue - cost
            margin = float((profit / revenue) * 100) if revenue else 0
            status = 'success' if margin >= 50 else 'warning' if margin >= 20 else 'danger'
            items.append(ProjectProfitabilityItem(
                project_name=p.name,
                revenue=revenue,
                cost=cost,
                profit=profit,
                margin=round(margin, 1),
                status=status
            ))
        return items

    # -------------------------------------------------------------------------
    # Expenses CRUD
    # -------------------------------------------------------------------------

    async def list_expenses(
        self,
        period: Optional[str] = None,
        search: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Expense], int]:
        """List expenses with filters and pagination."""
        stmt = select(Expense)
        count_stmt = select(func.count()).select_from(Expense)

        filters = []
        if period:
            start, end = self._get_period_range(period)
            filters.append(Expense.expense_date >= start)
            filters.append(Expense.expense_date <= end)
        if category:
            filters.append(Expense.category == category)
        if search:
            filters.append(
                Expense.description.ilike(f"%{search}%")
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.order_by(desc(Expense.expense_date)).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        expenses = result.scalars().all()

        total = await self.db.scalar(count_stmt) or 0

        return expenses, total

    async def create_expense(self, data: ExpenseCreate) -> Expense:
        """Create a new expense."""
        expense = Expense(
            project_id=data.project_id,
            category=data.category,
            description=data.description,
            amount=data.amount,
            expense_date=data.expense_date
        )
        self.db.add(expense)
        await self.db.flush()
        return expense

    async def get_expense(self, expense_id: UUID) -> Expense | None:
        """Get expense by ID."""
        return await self.db.get(Expense, expense_id)

    async def update_expense(self, expense_id: UUID, data: ExpenseUpdate) -> Expense | None:
        """Update an expense."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(expense, key, value)
        await self.db.flush()
        return expense

    async def delete_expense(self, expense_id: UUID) -> bool:
        """Delete an expense."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return False
        await self.db.delete(expense)
        await self.db.flush()
        return True