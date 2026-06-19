# schemas/expense.py
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from typing import Optional


class ExpenseCreate(BaseModel):
    project_id: Optional[UUID] = None
    category: str = Field(..., max_length=100)
    description: str = Field(..., max_length=1000)
    amount: Decimal = Field(..., gt=0)
    expense_date: date = Field(default_factory=date.today)


class ExpenseUpdate(BaseModel):
    project_id: Optional[UUID] = None
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    amount: Optional[Decimal] = Field(None, gt=0)
    expense_date: Optional[date] = None


class ExpenseResponse(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    category: str
    description: str
    amount: Decimal
    expense_date: date
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}