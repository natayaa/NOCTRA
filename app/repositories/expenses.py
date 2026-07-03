# repositories/expenses.py
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func, desc, or_

from models.expenses import Expense
from schemas.constants import ExpenseCategory, ExpenseStatus


class ExpenseRepository:
    """
    Repository for Expense model.
    Handles all database operations related to expenses.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    async def create(self, expense: Expense) -> Expense:
        """Create a new expense."""
        self.db.add(expense)
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def get(self, expense_id: UUID) -> Optional[Expense]:
        """Get expense by ID."""
        return await self.db.get(Expense, expense_id)

    async def update(self, expense_id: UUID, data: dict) -> Optional[Expense]:
        """Update expense with given data dict."""
        expense = await self.get(expense_id)
        if not expense:
            return None
            
        for key, value in data.items():
            if hasattr(expense, key):
                setattr(expense, key, value)
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def delete(self, expense_id: UUID) -> bool:
        """Delete expense by ID."""
        stmt = delete(Expense).where(Expense.id == expense_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    async def list_with_filters(
        self,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        project_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Expense], int]:
        """
        List expenses with optional filters and pagination.
        Returns (expenses, total_count).
        """
        stmt = select(Expense)
        count_stmt = select(func.count()).select_from(Expense)

        filters = []
        if period_start:
            filters.append(Expense.expense_date >= period_start)
        if period_end:
            filters.append(Expense.expense_date <= period_end)
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

    async def get_total_by_period(
        self, 
        period_start: date, 
        period_end: date,
        status: Optional[str] = None
    ) -> Decimal:
        """Get total expenses in a period."""
        filters = [
            Expense.expense_date >= period_start,
            Expense.expense_date <= period_end
        ]
        if status:
            filters.append(Expense.status == status)
            
        stmt = select(func.sum(Expense.amount)).where(and_(*filters))
        result = await self.db.execute(stmt)
        return result.scalar() or Decimal(0)

    async def get_total_by_category(
        self, 
        period_start: date, 
        period_end: date
    ) -> List[tuple]:
        """Get total expenses grouped by category."""
        stmt = select(
            Expense.category,
            func.sum(Expense.amount).label('total')
        ).where(
            Expense.expense_date >= period_start,
            Expense.expense_date <= period_end
        ).group_by(Expense.category).order_by(desc('total'))
        result = await self.db.execute(stmt)
        return result.all()

    async def get_total_by_status(
        self,
        period_start: date,
        period_end: date
    ) -> List[tuple]:
        """Get total expenses grouped by status."""
        stmt = select(
            Expense.status,
            func.sum(Expense.amount).label('total')
        ).where(
            Expense.expense_date >= period_start,
            Expense.expense_date <= period_end
        ).group_by(Expense.status).order_by(desc('total'))
        result = await self.db.execute(stmt)
        return result.all()

    async def get_monthly_totals(
        self, 
        period_start: date, 
        period_end: date
    ) -> List[tuple]:
        """Get total expenses per month."""
        stmt = select(
            func.date_trunc('month', Expense.expense_date).label('month'),
            func.sum(Expense.amount).label('total')
        ).where(
            Expense.expense_date >= period_start,
            Expense.expense_date <= period_end
        ).group_by('month').order_by('month')
        result = await self.db.execute(stmt)
        return result.all()

    async def get_by_project(
        self, 
        project_id: UUID, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Expense]:
        """Get expenses by project ID."""
        stmt = select(Expense).where(
            Expense.project_id == project_id
        ).order_by(desc(Expense.expense_date)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_project_expense_summary(self, project_id: UUID) -> dict:
        """Get expense summary for a project."""
        stmt = select(
            func.sum(Expense.amount).label('total'),
            func.count().label('count'),
            Expense.status
        ).where(
            Expense.project_id == project_id
        ).group_by(Expense.status)
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        summary = {
            "total": Decimal(0),
            "count": 0,
            "by_status": {}
        }
        
        for row in rows:
            summary["total"] += row.total or Decimal(0)
            summary["count"] += row.count or 0
            summary["by_status"][row.status] = {
                "total": row.total or Decimal(0),
                "count": row.count or 0
            }
            
        return summary

    async def count_by_category(
        self, 
        period_start: date, 
        period_end: date
    ) -> dict:
        """Count expenses per category (for dashboard)."""
        rows = await self.get_total_by_category(period_start, period_end)
        return {row.category: row.total for row in rows}

    async def approve_expense(self, expense_id: UUID, approved_by: str) -> Optional[Expense]:
        """Approve an expense."""
        expense = await self.get(expense_id)
        if not expense:
            return None
        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = approved_by
        expense.approved_at = date.today()
        await self.db.flush()
        await self.db.refresh(expense)
        return expense

    async def mark_as_paid(self, expense_id: UUID) -> Optional[Expense]:
        """Mark expense as paid."""
        expense = await self.get(expense_id)
        if not expense:
            return None
        expense.status = ExpenseStatus.PAID
        await self.db.flush()
        await self.db.refresh(expense)
        return expense