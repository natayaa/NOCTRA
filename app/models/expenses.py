# models/expense.py
from sqlalchemy import String, Text, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal
from datetime import date
from uuid import UUID

from database.base import Base, UUIDMixin, TimestampMixin
from models.projects import Project


class Expense(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_expenses"

    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    # relationships
    project = relationship("Project")  # jika Project punya relasi ini

    def __repr__(self):
        return f"<Expense {self.description[:20]} - {self.amount}>" 