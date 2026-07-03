# routers/budgeting.py
from uuid import UUID
from fastapi import APIRouter, Query, HTTPException, status

from database.session import SessionDep
from schemas.base_response import BaseResponse, PaginatedResponse
from schemas.expenses import ExpenseCreate, ExpenseUpdate, ExpenseResponse
from schemas.budgeting import (
    SummaryResponse, KPIsResponse,
    MonthlyExpensePoint, BreakdownItem,
    CashflowPoint, ProjectProfitabilityItem
)
from services.budgeting import BudgetingService

budgeting = APIRouter(prefix="/api/budgeting", tags=["Budgeting"])


# -------------------------------------------------------------------------
# Summary & KPIs
# -------------------------------------------------------------------------

@budgeting.get("/summary", response_model=BaseResponse)
async def get_summary(
    period: str = Query('month', description="month, last_month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    service = BudgetingService(db)
    data = await service.get_summary(period)
    return BaseResponse(data=data.model_dump())


@budgeting.get("/kpis", response_model=BaseResponse)
async def get_kpis(
    period: str = Query('month', description="month, last_month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    service = BudgetingService(db)
    data = await service.get_kpis(period)
    return BaseResponse(data=data.model_dump())


@budgeting.get("/expense-summary", response_model=BaseResponse)
async def get_expense_summary(
    period: str = Query('month', description="month, last_month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    """Get expense summary for dashboard."""
    service = BudgetingService(db)
    data = await service.get_expense_summary(period)
    return BaseResponse(data=data)


# -------------------------------------------------------------------------
# Charts
# -------------------------------------------------------------------------

@budgeting.get("/charts/monthly-expenses", response_model=BaseResponse)
async def get_monthly_expenses(
    period: str = Query('month', description="month, last_month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    service = BudgetingService(db)
    data = await service.get_monthly_expenses(period)
    return BaseResponse(data=[item.model_dump() for item in data])


@budgeting.get("/charts/expense-breakdown", response_model=BaseResponse)
async def get_expense_breakdown(
    period: str = Query('month', description="month, last_month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    service = BudgetingService(db)
    data = await service.get_expense_breakdown(period)
    return BaseResponse(data=[item.model_dump() for item in data])


@budgeting.get("/charts/cashflow", response_model=BaseResponse)
async def get_cashflow(
    period: str = Query('month', description="month, last_month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    service = BudgetingService(db)
    data = await service.get_cashflow(period)
    return BaseResponse(data=[item.model_dump() for item in data])


# -------------------------------------------------------------------------
# Project Profitability
# -------------------------------------------------------------------------

@budgeting.get("/profitability", response_model=BaseResponse)
async def get_project_profitability(
    db: SessionDep = None
) -> BaseResponse:
    service = BudgetingService(db)
    data = await service.get_project_profitability()
    return BaseResponse(data=[item.model_dump() for item in data])


# -------------------------------------------------------------------------
# Expenses CRUD
# -------------------------------------------------------------------------

@budgeting.get("/expenses", response_model=BaseResponse)
async def list_expenses(
    period: str = Query('month', description="month, last_month, quarter, year"),
    search: str | None = Query(None, description="Search in description"),
    category: str | None = Query(None, description="Filter by category"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: SessionDep = None
) -> BaseResponse:
    service = BudgetingService(db)
    expenses, total = await service.list_expenses(
        period=period,
        search=search,
        category=category,
        status=status,
        limit=limit,
        offset=(page - 1) * limit
    )
    # Enrich with project name
    data = []
    for exp in expenses:
        project_name = exp.project.name if exp.project else None
        data.append({
            **ExpenseResponse.model_validate(exp).model_dump(),
            "project_name": project_name
        })
    return BaseResponse(data={
        "items": data,
        "total": total,
        "page": page,
        "page_size": limit
    })


@budgeting.post("/expenses", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    request: ExpenseCreate,
    db: SessionDep
) -> BaseResponse:
    service = BudgetingService(db)
    expense = await service.create_expense(request)
    await db.commit()
    return BaseResponse(data={"id": str(expense.id)})


@budgeting.get("/expenses/{expense_id}", response_model=BaseResponse)
async def get_expense(
    expense_id: UUID,
    db: SessionDep
) -> BaseResponse:
    service = BudgetingService(db)
    expense = await service.get_expense(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    project_name = expense.project.name if expense.project else None
    data = {
        **ExpenseResponse.model_validate(expense).model_dump(),
        "project_name": project_name
    }
    return BaseResponse(data=data)


@budgeting.put("/expenses/{expense_id}", response_model=BaseResponse)
async def update_expense(
    expense_id: UUID,
    request: ExpenseUpdate,
    db: SessionDep
) -> BaseResponse:
    service = BudgetingService(db)
    expense = await service.update_expense(expense_id, request)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.commit()
    return BaseResponse(data={"id": str(expense.id)})


@budgeting.delete("/expenses/{expense_id}", response_model=BaseResponse)
async def delete_expense(
    expense_id: UUID,
    db: SessionDep
) -> BaseResponse:
    service = BudgetingService(db)
    deleted = await service.delete_expense(expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.commit()
    return BaseResponse(data={"id": str(expense_id)})


@budgeting.patch("/expenses/{expense_id}/approve", response_model=BaseResponse)
async def approve_expense(
    db: SessionDep,
    expense_id: UUID,
    approved_by: str = Query(..., description="Name of approver")
) -> BaseResponse:
    service = BudgetingService(db)
    expense = await service.approve_expense(expense_id, approved_by)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.commit()
    return BaseResponse(data={"id": str(expense.id), "status": "approved"})


@budgeting.patch("/expenses/{expense_id}/pay", response_model=BaseResponse)
async def mark_expense_as_paid(
    expense_id: UUID,
    db: SessionDep
) -> BaseResponse:
    service = BudgetingService(db)
    expense = await service.mark_as_paid(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.commit()
    return BaseResponse(data={"id": str(expense.id), "status": "paid"})