# models/expenses.py
from sqlalchemy import String, Text, Numeric, Date, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal
from datetime import date
from uuid import UUID

from database.base import Base, UUIDMixin, TimestampMixin
from schemas.constants import ExpenseCategory, ExpenseStatus


class Expense(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_expenses"

    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sub_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    
    # Additional fields
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default=ExpenseStatus.PENDING,
        index=True
    )
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    receipt_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Relationships
    # Gunakan back_populates yang sesuai dengan nama di Project
    project = relationship("Project", back_populates="expense_items")

    def __repr__(self):
        return f"<Expense {self.id} - {self.description[:30]} - {self.amount}>"