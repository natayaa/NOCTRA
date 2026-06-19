# app/services/inventory/dashboard_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.inventory_items import InventoryItems
from models.inventory_stock_movement import StockMovement


class DashboardService:
    async def get_kpis(self, db: AsyncSession):
        total_skus = await db.scalar(select(func.count(InventoryItems.id)))

        total_value = await db.scalar(
            select(func.sum(InventoryItems.current_stock * InventoryItems.cost_price))
        )

        low_stock = await db.scalar(
            select(func.count(InventoryItems.id)).where(InventoryItems.current_stock <= InventoryItems.min_stock_threshold)
        )

        return {
            "total_skus": total_skus or 0,
            "total_inventory_value": float(total_value or 0),
            "low_stock_items": low_stock or 0,
        }

    async def monthly_usage(self, db: AsyncSession):
        result = await db.execute(
            select(
                StockMovement.item_id,
                func.sum(StockMovement.quantity).label("used")
            )
            .where(StockMovement.type == "OUT")
            .group_by(StockMovement.item_id)
        )

        return result.all()
    
    async def get_stock_alerts(self, db: AsyncSession):
        items = await db.execute(
            select(InventoryItems).where(
                InventoryItems.current_stock <= InventoryItems.min_stock_threshold
            )
        )
        items = items.scalars().all()
        alerts = []
        for item in items:
            threshold = item.min_stock_threshold
            critical = item.current_stock <= threshold // 2
            alerts.append({
                "id": str(item.id),
                "name": item.name,
                "category": item.category,
                "current_stock": item.current_stock,
                "min_stock_threshold": threshold,
                "status": "critical" if critical else "low"
            })
        return alerts