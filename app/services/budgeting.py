# services/budgeting.py
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, desc, or_

from models.projects import Project
from models.expenses import Expense
from models.inventory import InventoryMaterialUsage, InventoryItem

from schemas.expenses import ExpenseCreate, ExpenseUpdate
from schemas.budgeting import (
    SummaryResponse, KPIsResponse,
    MonthlyExpensePoint, BreakdownItem,
    CashflowPoint, ProjectProfitabilityItem,
    BudgetingExpenseCreate, BudgetingExpenseUpdate, BudgetingExpenseResponse
)
from schemas.constants import ProjectStatus, ExpenseStatus, ExpenseCategory


class BudgetingService:
    """
    Service for budgeting & financial management.
    Aggregates data from Projects, Expenses, and Inventory.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

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

        # Active projects
        active_projects = await self.db.scalar(
            select(func.count(Project.id)).where(
                Project.status.in_([ProjectStatus.ACTIVE, ProjectStatus.IN_PROGRESS])
            )
        ) or 0

        # Pending payments (profit from completed projects)
        pending = await self.db.scalar(
            select(func.coalesce(func.sum(Project.actual_revenue - Project.actual_cost), 0))
            .where(Project.status == ProjectStatus.COMPLETED)
        ) or Decimal(0)

        # Material cost ratio = total material expenses / total revenue
        material_expenses = await self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(
                Expense.category == ExpenseCategory.MATERIALS,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
                Expense.status == ExpenseStatus.PAID
            )
        ) or Decimal(0)

        total_revenue = await self.db.scalar(
            select(func.coalesce(func.sum(Project.actual_revenue), 1))
            .where(Project.status == ProjectStatus.COMPLETED)
        ) or Decimal(1)

        material_ratio = float((material_expenses / total_revenue) * 100)

        # Average project profit
        avg_profit = await self.db.scalar(
            select(func.coalesce(func.avg(Project.actual_revenue - Project.actual_cost), 0))
            .where(Project.status == ProjectStatus.COMPLETED)
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
            select(func.coalesce(func.sum(Project.actual_revenue), 0))
            .where(
                Project.status == ProjectStatus.COMPLETED,
                Project.completed_at >= start,
                Project.completed_at <= end
            )
        ) or Decimal(0)

        # Expenses from Expense table in period
        expenses = await self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(
                Expense.expense_date >= start,
                Expense.expense_date <= end,
                Expense.status == ExpenseStatus.PAID
            )
        ) or Decimal(0)

        net_profit = revenue - expenses

        # Cash available = total revenue all time - total expenses all time
        total_revenue = await self.db.scalar(
            select(func.coalesce(func.sum(Project.actual_revenue), 0))
        ) or Decimal(0)
        total_expenses = await self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(Expense.status == ExpenseStatus.PAID)
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

        stmt = select(
            func.date_trunc('month', Expense.expense_date).label('month'),
            func.coalesce(func.sum(Expense.amount), 0).label('total')
        ).where(
            Expense.expense_date >= start,
            Expense.expense_date <= end,
            Expense.status == ExpenseStatus.PAID
        ).group_by('month').order_by('month')

        result = await self.db.execute(stmt)
        rows = result.all()

        data = []
        for row in rows:
            month = row.month.strftime('%b %Y')
            data.append(MonthlyExpensePoint(
                month=month, amount=row.total or Decimal(0)
            ))
        return data

    async def get_expense_breakdown(self, period: str) -> List[BreakdownItem]:
        """Return expense breakdown by category for pie chart."""
        start, end = self._get_period_range(period)

        stmt = select(
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0).label('total')
        ).where(
            Expense.expense_date >= start,
            Expense.expense_date <= end,
            Expense.status == ExpenseStatus.PAID
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
            func.coalesce(func.sum(Project.actual_revenue), 0).label('revenue')
        ).where(
            Project.status == ProjectStatus.COMPLETED,
            Project.completed_at >= start,
            Project.completed_at <= end
        ).group_by('month').order_by('month')

        # Expenses per month from Expense
        exp_stmt = select(
            func.date_trunc('month', Expense.expense_date).label('month'),
            func.coalesce(func.sum(Expense.amount), 0).label('expenses')
        ).where(
            Expense.expense_date >= start,
            Expense.expense_date <= end,
            Expense.status == ExpenseStatus.PAID
        ).group_by('month').order_by('month')

        rev_result = await self.db.execute(rev_stmt)
        exp_result = await self.db.execute(exp_stmt)

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
            Project.status == ProjectStatus.COMPLETED
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
        status: Optional[str] = None,
        project_id: Optional[UUID] = None,
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
        if status:
            filters.append(Expense.status == status)
        if project_id:
            filters.append(Expense.project_id == project_id)
        if search:
            filters.append(
                or_(
                    Expense.description.ilike(f"%{search}%"),
                    Expense.reference_number.ilike(f"%{search}%"),
                    Expense.notes.ilike(f"%{search}%")
                )
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
            expense_date=data.expense_date,
            status=data.status or ExpenseStatus.PENDING,
            payment_method=data.payment_method,
            reference_number=data.reference_number,
            notes=data.notes
        )
        self.db.add(expense)
        await self.db.flush()
        await self.db.refresh(expense)
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
            if hasattr(expense, key):
                setattr(expense, key, value)
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def delete_expense(self, expense_id: UUID) -> bool:
        """Delete an expense."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return False
        await self.db.delete(expense)
        await self.db.flush()
        return True

    async def approve_expense(self, expense_id: UUID, approved_by: str) -> Expense | None:
        """Approve an expense."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return None
        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = approved_by
        expense.approved_at = date.today()
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def mark_as_paid(self, expense_id: UUID) -> Expense | None:
        """Mark expense as paid."""
        expense = await self.get_expense(expense_id)
        if not expense:
            return None
        expense.status = ExpenseStatus.PAID
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def get_expense_summary(self, period: str) -> dict:
        """Get expense summary for dashboard."""
        start, end = self._get_period_range(period)
        
        # Total expenses
        total = await self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(
                Expense.expense_date >= start,
                Expense.expense_date <= end,
                Expense.status == ExpenseStatus.PAID
            )
        ) or Decimal(0)
        
        # By category
        by_category = await self.db.execute(
            select(
                Expense.category,
                func.coalesce(func.sum(Expense.amount), 0).label('total')
            )
            .where(
                Expense.expense_date >= start,
                Expense.expense_date <= end,
                Expense.status == ExpenseStatus.PAID
            )
            .group_by(Expense.category)
            .order_by(func.sum(Expense.amount).desc())
        )
        
        return {
            "total": total,
            "by_category": [
                {"category": row.category, "amount": row.total}
                for row in by_category
            ],
            "period": period
        }