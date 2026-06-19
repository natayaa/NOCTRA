# routers/analytics.py
from fastapi import APIRouter, Query, HTTPException, status

from database.session import SessionDep
from schemas.base_response import BaseResponse
from schemas.analytics import (
    KPIsResponse,
    RevenueProfitResponse,
    ConversionResponse,
    ServiceBreakdownResponse,
    MaterialConsumptionResponse,
    TopServicesResponse,
    OperationalKPIsResponse,
    InsightsResponse
)
from services.analytics import AnalyticsService

analytics = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@analytics.get("/kpis", response_model=BaseResponse)
async def get_kpis(
    period: str = Query('week', description="Period: today, week, month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    """
    Get main KPIs: revenue, profit, conversion rate, completed projects, etc.
    """
    service = AnalyticsService(db)
    data = await service.get_kpis(period)
    return BaseResponse(data=data.model_dump())


@analytics.get("/revenue-profit", response_model=BaseResponse)
async def get_revenue_profit(
    period: str = Query('week', description="Period: today, week, month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    """
    Get revenue vs profit data for line chart.
    """
    service = AnalyticsService(db)
    data = await service.get_revenue_profit(period)
    return BaseResponse(data=data.model_dump())


@analytics.get("/conversion", response_model=BaseResponse)
async def get_conversion(
    period: str = Query('week', description="Period: today, week, month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    """
    Get inquiry vs conversion data for line chart.
    """
    service = AnalyticsService(db)
    data = await service.get_conversion(period)
    return BaseResponse(data=data.model_dump())


@analytics.get("/service-breakdown", response_model=BaseResponse)
async def get_service_breakdown(
    db: SessionDep = None
) -> BaseResponse:
    """
    Get service distribution (pie chart).
    """
    service = AnalyticsService(db)
    data = await service.get_service_breakdown()
    return BaseResponse(data=data.model_dump())


@analytics.get("/material-consumption", response_model=BaseResponse)
async def get_material_consumption(
    db: SessionDep = None
) -> BaseResponse:
    """
    Get material consumption breakdown (pie chart).
    """
    service = AnalyticsService(db)
    data = await service.get_material_consumption()
    return BaseResponse(data=data.model_dump())


@analytics.get("/top-services", response_model=BaseResponse)
async def get_top_services(
    limit: int = Query(5, ge=1, le=20, description="Number of top services to return"),
    db: SessionDep = None
) -> BaseResponse:
    """
    Get top services by revenue.
    """
    service = AnalyticsService(db)
    data = await service.get_top_services(limit)
    return BaseResponse(data=data.model_dump())


@analytics.get("/operational-kpis", response_model=BaseResponse)
async def get_operational_kpis(
    db: SessionDep = None
) -> BaseResponse:
    """
    Get operational KPIs: avg duration, success rate, margin, turnover.
    """
    service = AnalyticsService(db)
    data = await service.get_operational_kpis()
    return BaseResponse(data=data.model_dump())


@analytics.get("/insights", response_model=BaseResponse)
async def get_insights(
    period: str = Query('week', description="Period for insight context"),
    db: SessionDep = None
) -> BaseResponse:
    """
    Get actionable insights based on current data.
    """
    service = AnalyticsService(db)
    data = await service.get_insights(period)
    return BaseResponse(data=data.model_dump())


# Optional: One endpoint to get all data at once
@analytics.get("/full", response_model=BaseResponse)
async def get_full_analytics(
    period: str = Query('week', description="Period: today, week, month, quarter, year"),
    db: SessionDep = None
) -> BaseResponse:
    """
    Get all analytics data in one request (for dashboard load).
    """
    service = AnalyticsService(db)
    kpis = await service.get_kpis(period)
    revenue_profit = await service.get_revenue_profit(period)
    conversion = await service.get_conversion(period)
    service_breakdown = await service.get_service_breakdown()
    material_consumption = await service.get_material_consumption()
    top_services = await service.get_top_services()
    operational_kpis = await service.get_operational_kpis()
    insights = await service.get_insights(period)

    return BaseResponse(data={
        "period": period,
        "kpis": kpis.model_dump(),
        "revenue_profit": revenue_profit.model_dump(),
        "conversion": conversion.model_dump(),
        "service_breakdown": service_breakdown.model_dump(),
        "material_consumption": material_consumption.model_dump(),
        "top_services": top_services.model_dump(),
        "operational_kpis": operational_kpis.model_dump(),
        "insights": insights.model_dump()
    })