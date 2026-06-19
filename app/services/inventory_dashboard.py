# services/inventory_dashboard.py
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.inventory_items import InventoryItems
from models.inventory_stock_movement import StockMovement


class InventoryDashboardService:
    """
    Service for inventory dashboard analytics.
    Provides KPIs, stock alerts, and usage statistics.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_kpis(self) -> dict:
        """
        Return key performance indicators:
        - total_skus: number of unique inventory items
        - total_inventory_value: total value of current stock
        - low_stock_items: count of items below or at threshold
        """
        total_skus = await self.db.scalar(select(func.count(InventoryItems.id)))

        total_value = await self.db.scalar(
            select(func.sum(InventoryItems.current_stock * InventoryItems.cost_price))
        )

        low_stock = await self.db.scalar(
            select(func.count(InventoryItems.id)).where(
                InventoryItems.current_stock <= InventoryItems.min_stock_threshold
            )
        )

        return {
            "total_skus": total_skus or 0,
            "total_inventory_value": float(total_value or Decimal(0)),
            "low_stock_items": low_stock or 0,
        }

    async def get_monthly_usage(self) -> list[dict]:
        """
        Get total usage (quantity) per item for the last 30 days.
        Returns list of {item_id, item_name, used_quantity}.
        """
        from datetime import datetime, timedelta

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        stmt = (
            select(
                InventoryItems.id,
                InventoryItems.name,
                func.sum(StockMovement.quantity).label("used_quantity"),
            )
            .join(InventoryItems, StockMovement.item_id == InventoryItems.id)
            .where(
                StockMovement.type == "out",
                StockMovement.created_at >= thirty_days_ago,
            )
            .group_by(InventoryItems.id, InventoryItems.name)
            .order_by(func.sum(StockMovement.quantity).desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "item_id": str(row.id),
                "item_name": row.name,
                "used_quantity": int(row.used_quantity or 0),
            }
            for row in rows
        ]

    async def get_stock_alerts(self) -> list[dict]:
        """
        Return items with stock at or below threshold.
        Items with stock <= half of threshold are marked as 'critical'.
        """
        stmt = select(InventoryItems).where(
            InventoryItems.current_stock <= InventoryItems.min_stock_threshold
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        alerts = []
        for item in items:
            threshold = item.min_stock_threshold or 0
            critical = threshold > 0 and item.current_stock <= (threshold // 2)

            alerts.append({
                "id": str(item.id),
                "name": item.name,
                "category": item.category,
                "current_stock": item.current_stock,
                "min_stock_threshold": threshold,
                "status": "critical" if critical else "low",
            })
        return alerts