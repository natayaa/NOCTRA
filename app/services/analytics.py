# services/analytics.py
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract

from models.projects import Project
from models.customer_inquiry import CustomerInquiry
from models.inventory_items import InventoryItems
from models.inventory_stock_movement import StockMovement
from models.inventory_material_usage import JobMaterialUsage
from models.price_list import PriceListItem

from schemas.analytics import (
    KPIsResponse, KPITrend,
    RevenueProfitResponse, RevenueProfitDataPoint,
    ConversionResponse, ConversionDataPoint,
    ServiceBreakdownResponse, ServiceBreakdownItem,
    MaterialConsumptionResponse, MaterialConsumptionItem,
    TopServicesResponse, TopServiceItem,
    OperationalKPIsResponse, OperationalKPIItem,
    InsightsResponse, InsightItem
)


class AnalyticsService:
    """
    Analytics service – mengumpulkan data dari berbagai modul.
    Setiap method bertanggung jawab atas satu jenis data.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Helper: Periode
    # -------------------------------------------------------------------------

    def _get_period_range(self, period: str) -> tuple[datetime, datetime]:
        """Return start and end datetime for a given period."""
        now = datetime.now()
        if period == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == 'week':
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == 'month':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == 'quarter':
            month = now.month
            quarter_start_month = ((month - 1) // 3) * 3 + 1
            start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == 'year':
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        else:
            # default: last 30 days
            start = now - timedelta(days=30)
            end = now
        return start, end

    async def _get_previous_period_range(self, period: str) -> tuple[datetime, datetime]:
        """Get previous period range for trend calculation."""
        start, end = self._get_period_range(period)
        duration = end - start
        prev_end = start
        prev_start = prev_end - duration
        return prev_start, prev_end

    # -------------------------------------------------------------------------
    # KPIs
    # -------------------------------------------------------------------------

    async def get_kpis(self, period: str) -> KPIsResponse:
        """Calculate main KPIs: revenue, profit, conversion rate, completed projects."""
        start, end = self._get_period_range(period)
        prev_start, prev_end = await self._get_previous_period_range(period)

        # 1. Revenue & Profit (from projects)
        revenue_stmt = select(func.sum(Project.actual_revenue)).where(
            Project.completed_at >= start,
            Project.completed_at <= end
        )
        revenue = (await self.db.execute(revenue_stmt)).scalar() or Decimal(0)

        profit_stmt = select(func.sum(Project.actual_revenue - Project.actual_cost)).where(
            Project.completed_at >= start,
            Project.completed_at <= end
        )
        profit = (await self.db.execute(profit_stmt)).scalar() or Decimal(0)

        # Previous period for trends
        prev_revenue_stmt = select(func.sum(Project.actual_revenue)).where(
            Project.completed_at >= prev_start,
            Project.completed_at <= prev_end
        )
        prev_revenue = (await self.db.execute(prev_revenue_stmt)).scalar() or Decimal(0)

        # 2. Conversion rate (inquiries -> projects)
        total_inquiries = await self.db.scalar(
            select(func.count(CustomerInquiry.id)).where(
                CustomerInquiry.created_at >= start,
                CustomerInquiry.created_at <= end
            )
        ) or 0
        converted = await self.db.scalar(
            select(func.count(CustomerInquiry.id)).where(
                CustomerInquiry.status == 'converted',
                CustomerInquiry.created_at >= start,
                CustomerInquiry.created_at <= end
            )
        ) or 0
        conversion_rate = (converted / total_inquiries * 100) if total_inquiries > 0 else 0

        # Previous conversion
        prev_inquiries = await self.db.scalar(
            select(func.count(CustomerInquiry.id)).where(
                CustomerInquiry.created_at >= prev_start,
                CustomerInquiry.created_at <= prev_end
            )
        ) or 1
        prev_converted = await self.db.scalar(
            select(func.count(CustomerInquiry.id)).where(
                CustomerInquiry.status == 'converted',
                CustomerInquiry.created_at >= prev_start,
                CustomerInquiry.created_at <= prev_end
            )
        ) or 0
        prev_conversion_rate = (prev_converted / prev_inquiries * 100) if prev_inquiries > 0 else 0

        # 3. Completed projects
        completed = await self.db.scalar(
            select(func.count(Project.id)).where(
                Project.status == 'completed',
                Project.completed_at >= start,
                Project.completed_at <= end
            )
        ) or 0
        prev_completed = await self.db.scalar(
            select(func.count(Project.id)).where(
                Project.status == 'completed',
                Project.completed_at >= prev_start,
                Project.completed_at <= prev_end
            )
        ) or 0

        # 4. Low stock items (from inventory)
        low_stock = await self.db.scalar(
            select(func.count(InventoryItems.id)).where(
                InventoryItems.current_stock <= InventoryItems.min_stock_threshold,
                InventoryItems.status == 'active'
            )
        ) or 0

        # 5. Active projects (in progress)
        active_projects = await self.db.scalar(
            select(func.count(Project.id)).where(
                Project.status.in_(['preparation', 'painting', 'assembly'])
            )
        ) or 0

        # Build response
        return KPIsResponse(
            total_revenue=KPITrend(
                value=float(revenue),
                trend_percent=self._calc_trend(revenue, prev_revenue)
            ),
            net_profit=KPITrend(
                value=float(profit),
                trend_percent=self._calc_trend(profit, profit)  # placeholder, bisa dihitung dari prev profit
            ),
            conversion_rate=KPITrend(
                value=round(conversion_rate, 1),
                trend_percent=round(conversion_rate - prev_conversion_rate, 1)
            ),
            completed_projects=KPITrend(
                value=completed,
                trend_percent=completed - prev_completed
            ),
            low_stock_items=low_stock,
            active_projects=active_projects,
            period=period
        )

    def _calc_trend(self, current: Decimal | float, previous: Decimal | float) -> float:
        if not previous:
            return 0
        return float(((current - previous) / previous) * 100)

    # -------------------------------------------------------------------------
    # Revenue vs Profit Chart
    # -------------------------------------------------------------------------

    async def get_revenue_profit(self, period: str) -> RevenueProfitResponse:
        """Get revenue vs profit data for line chart."""
        # Untuk chart, kita butuh data agregat per unit waktu (hari/bulan/tahun)
        # Tergantung period: week -> daily, month -> weekly, year -> monthly
        start, end = self._get_period_range(period)
        unit = self._get_chart_unit(period)

        # Build query based on unit
        if unit == 'day':
            # Group by day
            stmt = select(
                func.date_trunc('day', Project.completed_at).label('date'),
                func.sum(Project.actual_revenue).label('revenue'),
                func.sum(Project.actual_revenue - Project.actual_cost).label('profit')
            ).where(
                Project.status == 'completed',
                Project.completed_at >= start,
                Project.completed_at <= end
            ).group_by('date').order_by('date')
        elif unit == 'week':
            stmt = select(
                func.date_trunc('week', Project.completed_at).label('date'),
                func.sum(Project.actual_revenue).label('revenue'),
                func.sum(Project.actual_revenue - Project.actual_cost).label('profit')
            ).where(
                Project.status == 'completed',
                Project.completed_at >= start,
                Project.completed_at <= end
            ).group_by('date').order_by('date')
        else:  # month
            stmt = select(
                func.date_trunc('month', Project.completed_at).label('date'),
                func.sum(Project.actual_revenue).label('revenue'),
                func.sum(Project.actual_revenue - Project.actual_cost).label('profit')
            ).where(
                Project.status == 'completed',
                Project.completed_at >= start,
                Project.completed_at <= end
            ).group_by('date').order_by('date')

        result = await self.db.execute(stmt)
        rows = result.all()

        # Build labels and data
        data_points = []
        for row in rows:
            label = row.date.strftime('%Y-%m-%d')
            if unit == 'week':
                label = f"Week {row.date.isocalendar()[1]}"
            elif unit == 'month':
                label = row.date.strftime('%b %Y')
            data_points.append(
                RevenueProfitDataPoint(
                    label=label,
                    revenue=float(row.revenue or 0),
                    profit=float(row.profit or 0)
                )
            )

        return RevenueProfitResponse(period=period, data=data_points)

    def _get_chart_unit(self, period: str) -> str:
        if period in ['today', 'week']:
            return 'day'
        elif period == 'month':
            return 'week'
        else:
            return 'month'

    # -------------------------------------------------------------------------
    # Conversion Chart
    # -------------------------------------------------------------------------

    async def get_conversion(self, period: str) -> ConversionResponse:
        """Get inquiry vs conversion data for line chart."""
        start, end = self._get_period_range(period)
        unit = self._get_chart_unit(period)

        # Inquiries per unit
        inq_stmt = select(
            func.date_trunc(unit, CustomerInquiry.created_at).label('date'),
            func.count(CustomerInquiry.id).label('count')
        ).where(
            CustomerInquiry.created_at >= start,
            CustomerInquiry.created_at <= end
        ).group_by('date').order_by('date')

        # Conversions per unit
        conv_stmt = select(
            func.date_trunc(unit, CustomerInquiry.created_at).label('date'),
            func.count(CustomerInquiry.id).label('count')
        ).where(
            CustomerInquiry.status == 'converted',
            CustomerInquiry.created_at >= start,
            CustomerInquiry.created_at <= end
        ).group_by('date').order_by('date')

        inq_result = await self.db.execute(inq_stmt)
        conv_result = await self.db.execute(conv_stmt)

        # Build dicts for easy merge
        inq_map = {row.date: row.count for row in inq_result}
        conv_map = {row.date: row.count for row in conv_result}

        all_dates = sorted(set(inq_map.keys()) | set(conv_map.keys()))
        data_points = []
        for dt in all_dates:
            label = dt.strftime('%Y-%m-%d')
            if unit == 'week':
                label = f"Week {dt.isocalendar()[1]}"
            elif unit == 'month':
                label = dt.strftime('%b %Y')
            data_points.append(
                ConversionDataPoint(
                    label=label,
                    inquiries=inq_map.get(dt, 0),
                    conversions=conv_map.get(dt, 0)
                )
            )

        return ConversionResponse(period=period, data=data_points)

    # -------------------------------------------------------------------------
    # Service Breakdown (Pie Chart)
    # -------------------------------------------------------------------------

    async def get_service_breakdown(self) -> ServiceBreakdownResponse:
        """Get distribution of services by project count or revenue."""
        # Ambil data dari project_type di CustomerInquiry yang sudah converted
        stmt = select(
            CustomerInquiry.project_type,
            func.count(CustomerInquiry.id).label('count')
        ).where(
            CustomerInquiry.status == 'converted'
        ).group_by(CustomerInquiry.project_type).order_by(func.count(CustomerInquiry.id).desc())

        result = await self.db.execute(stmt)
        rows = result.all()

        total = sum(row.count for row in rows) or 1
        colors = ['#ff7b2c', '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6']

        items = []
        for idx, row in enumerate(rows):
            pct = (row.count / total) * 100
            items.append(
                ServiceBreakdownItem(
                    name=row.project_type or 'Other',
                    value=round(pct, 1),
                    color=colors[idx % len(colors)]
                )
            )
        return ServiceBreakdownResponse(items=items)

    # -------------------------------------------------------------------------
    # Material Consumption (Pie Chart)
    # -------------------------------------------------------------------------

    async def get_material_consumption(self) -> MaterialConsumptionResponse:
        """Get material consumption breakdown by total quantity used."""
        stmt = select(
            InventoryItems.name,
            func.sum(JobMaterialUsage.quantity).label('total_qty')
        ).join(JobMaterialUsage, JobMaterialUsage.item_id == InventoryItems.id)\
         .group_by(InventoryItems.id)\
         .order_by(func.sum(JobMaterialUsage.quantity).desc())

        result = await self.db.execute(stmt)
        rows = result.all()

        total = sum(row.total_qty for row in rows) or 1
        colors = ['#ff7b2c', '#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6']

        items = []
        for idx, row in enumerate(rows):
            pct = (row.total_qty / total) * 100
            items.append(
                MaterialConsumptionItem(
                    name=row.name or 'Unknown',
                    value=round(pct, 1),
                    color=colors[idx % len(colors)]
                )
            )
        return MaterialConsumptionResponse(items=items)

    # -------------------------------------------------------------------------
    # Top Services
    # -------------------------------------------------------------------------

    async def get_top_services(self, limit: int = 5) -> TopServicesResponse:
        """Get top services by revenue (from projects)."""
        # Hubungkan project ke inquiry untuk mendapatkan project_type
        stmt = select(
            CustomerInquiry.project_type,
            func.count(Project.id).label('projects'),
            func.sum(Project.actual_revenue).label('revenue')
        ).join(CustomerInquiry, CustomerInquiry.id == Project.inquiry_id)\
         .where(Project.status == 'completed')\
         .group_by(CustomerInquiry.project_type)\
         .order_by(func.sum(Project.actual_revenue).desc())\
         .limit(limit)

        result = await self.db.execute(stmt)
        rows = result.all()

        items = []
        for row in rows:
            items.append(
                TopServiceItem(
                    name=row.project_type or 'Other',
                    projects=row.projects or 0,
                    revenue=row.revenue or Decimal(0),
                    trend=None  # bisa dihitung jika ada data historical
                )
            )
        return TopServicesResponse(items=items)

    # -------------------------------------------------------------------------
    # Operational KPIs
    # -------------------------------------------------------------------------

    async def get_operational_kpis(self) -> OperationalKPIsResponse:
        """Get operational KPIs: avg duration, success rate, margin, turnover."""
        # 1. Avg project duration
        duration_stmt = select(
            func.avg(func.extract('epoch', Project.completed_at - Project.created_at) / 86400)
        ).where(Project.status == 'completed')
        avg_duration = (await self.db.execute(duration_stmt)).scalar() or 0

        # 2. Success rate (% completed vs total)
        total_projects = await self.db.scalar(select(func.count(Project.id))) or 1
        completed_projects = await self.db.scalar(
            select(func.count(Project.id)).where(Project.status == 'completed')
        ) or 0
        success_rate = (completed_projects / total_projects) * 100

        # 3. Avg margin (gunakan func.nullif untuk menghindari division by zero)
        margin_stmt = select(
            func.avg(
                (Project.actual_revenue - Project.actual_cost) / 
                func.nullif(Project.actual_revenue, 0) * 100
            )
        ).where(Project.status == 'completed')
        avg_margin = (await self.db.execute(margin_stmt)).scalar() or 0

        # 4. Inventory turnover (estimate)
        total_usage = await self.db.scalar(
            select(func.sum(JobMaterialUsage.quantity * InventoryItems.cost_price))
            .join(InventoryItems, JobMaterialUsage.item_id == InventoryItems.id)
        ) or 0
        avg_stock = await self.db.scalar(
            select(func.avg(InventoryItems.current_stock * InventoryItems.cost_price))
        ) or 1
        turnover = total_usage / avg_stock if avg_stock else 0

        items = [
            OperationalKPIItem(
                label='Avg Project Duration',
                value=f"{int(avg_duration)} days",
                progress=min(int(avg_duration * 10), 100),
                color=None
            ),
            OperationalKPIItem(
                label='Project Success Rate',
                value=f"{round(success_rate, 1)}%",
                progress=round(success_rate),
                color='success'
            ),
            OperationalKPIItem(
                label='Avg Margin',
                value=f"{round(avg_margin, 1)}%",
                progress=round(avg_margin),
                color='success' if avg_margin > 50 else 'warning'
            ),
            OperationalKPIItem(
                label='Inventory Turnover',
                value=f"{round(turnover, 1)}x",
                progress=min(round(turnover * 10), 100),
                color=None
            )
        ]
        return OperationalKPIsResponse(items=items)

    # -------------------------------------------------------------------------
    # Insights
    # -------------------------------------------------------------------------

    async def get_insights(self, period: str) -> InsightsResponse:
        """Generate actionable insights based on data."""
        kpis = await self.get_kpis(period)
        top_services = await self.get_top_services(3)

        insights = []

        # Revenue insight
        rev_trend = kpis.total_revenue.trend_percent or 0
        if rev_trend > 10:
            insights.append(InsightItem(
                icon='fa-arrow-up',
                message=f'Revenue <strong>+{rev_trend:.1f}%</strong> compared to previous period – excellent growth!',
                type='positive'
            ))
        elif rev_trend < -5:
            insights.append(InsightItem(
                icon='fa-arrow-down',
                message=f'Revenue <strong>{rev_trend:.1f}%</strong> compared to previous period – needs attention.',
                type='warning'
            ))

        # Low stock alert
        if kpis.low_stock_items and kpis.low_stock_items > 0:
            insights.append(InsightItem(
                icon='fa-exclamation-triangle',
                message=f'{kpis.low_stock_items} items <strong>low stock</strong> – reorder soon.',
                type='warning',
                link='/management/inventories'
            ))

        # Top service insight
        if top_services.items:
            top = top_services.items[0]
            insights.append(InsightItem(
                icon='fa-chart-pie',
                message=f'Top service: <strong>{top.name}</strong> with {top.projects} projects.',
                type='neutral'
            ))

        return InsightsResponse(items=insights)