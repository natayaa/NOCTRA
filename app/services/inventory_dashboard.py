# services/inventory_dashboard.py
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, case

from models.inventory import (
    InventoryItem,
    InventoryStockMovement,
    InventoryMaterialUsage,
    ProjectWorkshopTask,
)
from models.projects import Project
from models.price_list import PriceListItem
from models.expenses import Expense

from repositories.inventory_repository import (
    InventoryRepository,
    InventoryMaterialUsageRepository,
    InventoryStockMovementRepository,
    ProjectWorkshopJobRepository,
)
from schemas.constants import InventoryStatus, StockMovementType, ProjectStatus, ExpenseStatus


class InventoryDashboardService:
    """
    Service for inventory dashboard analytics.
    Provides KPIs, stock alerts, usage statistics, and movement insights.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory_item_repo = InventoryRepository(db)
        self.inventory_stock_repo = InventoryStockMovementRepository(db)
        self.usage_repo = InventoryMaterialUsageRepository(db)
        self.workshop_repo = ProjectWorkshopJobRepository(db)

    # ----------------------------------------------------------------------
    # Key Performance Indicators
    # ----------------------------------------------------------------------
    async def get_kpis(self) -> dict:
        """Get main inventory KPIs."""
        active_filter = InventoryItem.status == InventoryStatus.ACTIVE

        # Total active SKUs
        total_skus = await self.db.scalar(
            select(func.count(InventoryItem.id)).where(active_filter)
        ) or 0

        # Total inventory value (current_stock * cost_price)
        total_value = await self.db.scalar(
            select(func.coalesce(
                func.sum(InventoryItem.current_stock * InventoryItem.cost_price), 
                Decimal(0)
            ))
            .where(active_filter)
        ) or Decimal(0)

        # Low stock items (current_stock <= min_stock_threshold)
        low_stock = await self.db.scalar(
            select(func.count(InventoryItem.id))
            .where(
                active_filter,
                InventoryItem.current_stock <= InventoryItem.min_stock_threshold,
                InventoryItem.current_stock > 0
            )
        ) or 0

        # Out of stock items
        out_of_stock = await self.db.scalar(
            select(func.count(InventoryItem.id))
            .where(InventoryItem.status == InventoryStatus.OUT_OF_STOCK)
        ) or 0

        # Total material usage cost (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        total_usage_cost = await self.db.scalar(
            select(func.coalesce(func.sum(InventoryMaterialUsage.total_cost), Decimal(0)))
            .where(InventoryMaterialUsage.created_at >= thirty_days_ago)
        ) or Decimal(0)

        # Total material usage quantity (last 30 days)
        total_usage_qty = await self.db.scalar(
            select(func.coalesce(func.sum(InventoryMaterialUsage.quantity), Decimal(0)))
            .where(InventoryMaterialUsage.created_at >= thirty_days_ago)
        ) or Decimal(0)

        return {
            "total_skus": total_skus,
            "total_inventory_value": float(total_value),
            "low_stock_items": low_stock,
            "out_of_stock_items": out_of_stock,
            "total_usage_cost": float(total_usage_cost),
            "total_usage_quantity": float(total_usage_qty),
        }

    # ----------------------------------------------------------------------
    # Stock Alerts
    # ----------------------------------------------------------------------
    async def get_stock_alerts(self) -> list[dict]:
        """Get items that are low on stock or out of stock."""
        stmt = select(InventoryItem).where(
            or_(
                and_(
                    InventoryItem.status == InventoryStatus.ACTIVE,
                    InventoryItem.current_stock <= InventoryItem.min_stock_threshold,
                ),
                InventoryItem.status == InventoryStatus.OUT_OF_STOCK
            )
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        alerts = []
        for item in items:
            threshold = item.min_stock_threshold or Decimal(0)
            if item.status == InventoryStatus.OUT_OF_STOCK:
                status = "out_of_stock"
                severity = "critical"
            elif threshold > 0 and item.current_stock <= (threshold / Decimal(2)):
                status = "critical"
                severity = "critical"
            else:
                status = "low"
                severity = "warning"

            alerts.append({
                "id": str(item.id),
                "name": item.name,
                "category": item.category,
                "current_stock": float(item.current_stock),
                "min_stock_threshold": float(threshold),
                "unit": item.unit,
                "status": status,
                "severity": severity,
            })
        return alerts

    async def get_stock_alert_summary(self) -> dict:
        """Get summary of stock alerts."""
        alerts = await self.get_stock_alerts()
        
        critical = len([a for a in alerts if a["severity"] == "critical"])
        warning = len([a for a in alerts if a["severity"] == "warning"])
        
        return {
            "total_alerts": len(alerts),
            "critical": critical,
            "warning": warning,
            "alerts": alerts
        }

    # ----------------------------------------------------------------------
    # Usage Statistics
    # ----------------------------------------------------------------------
    async def get_monthly_usage(self) -> list[dict]:
        """Get monthly usage statistics (last 30 days)."""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        stmt = (
            select(
                InventoryItem.id,
                InventoryItem.name,
                InventoryItem.category,
                InventoryItem.unit,
                func.coalesce(
                    func.sum(InventoryStockMovement.quantity), Decimal(0)
                ).label("used_quantity"),
                func.coalesce(
                    func.sum(InventoryStockMovement.quantity * InventoryItem.cost_price), Decimal(0)
                ).label("used_cost"),
            )
            .join(InventoryItem, InventoryStockMovement.item_id == InventoryItem.id)
            .where(
                InventoryStockMovement.type == StockMovementType.USAGE,
                InventoryStockMovement.created_at >= thirty_days_ago,
            )
            .group_by(InventoryItem.id, InventoryItem.name, InventoryItem.category, InventoryItem.unit)
            .order_by(func.sum(InventoryStockMovement.quantity).desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "item_id": str(row.id),
                "item_name": row.name,
                "category": row.category,
                "unit": row.unit,
                "used_quantity": float(row.used_quantity or 0),
                "used_cost": float(row.used_cost or 0),
            }
            for row in rows
        ]

    async def get_top_used_items(self, days: int = 30, limit: int = 10) -> list[dict]:
        """Get top used items by quantity in a given period."""
        since = datetime.now() - timedelta(days=days)
        stmt = (
            select(
                InventoryItem.id,
                InventoryItem.name,
                InventoryItem.category,
                InventoryItem.unit,
                func.coalesce(
                    func.sum(InventoryMaterialUsage.quantity), Decimal(0)
                ).label("total_used"),
                func.coalesce(
                    func.sum(InventoryMaterialUsage.total_cost), Decimal(0)
                ).label("total_cost"),
                func.count(InventoryMaterialUsage.id).label("usage_count"),
            )
            .join(InventoryItem, InventoryMaterialUsage.item_id == InventoryItem.id)
            .where(InventoryMaterialUsage.created_at >= since)
            .group_by(InventoryItem.id, InventoryItem.name, InventoryItem.category, InventoryItem.unit)
            .order_by(func.sum(InventoryMaterialUsage.quantity).desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "item_id": str(row.id),
                "item_name": row.name,
                "category": row.category,
                "unit": row.unit,
                "total_used": float(row.total_used or 0),
                "total_cost": float(row.total_cost or 0),
                "usage_count": row.usage_count or 0,
            }
            for row in rows
        ]

    # ----------------------------------------------------------------------
    # Inventory Value by Category
    # ----------------------------------------------------------------------
    async def get_inventory_value_by_category(self) -> list[dict]:
        """Get inventory value grouped by category."""
        stmt = (
            select(
                InventoryItem.category,
                func.coalesce(
                    func.sum(InventoryItem.current_stock * InventoryItem.cost_price),
                    Decimal(0),
                ).label("total_value"),
                func.count(InventoryItem.id).label("item_count"),
                func.coalesce(
                    func.sum(InventoryItem.current_stock), Decimal(0)
                ).label("total_stock"),
            )
            .where(InventoryItem.status == InventoryStatus.ACTIVE)
            .group_by(InventoryItem.category)
            .order_by(
                func.sum(InventoryItem.current_stock * InventoryItem.cost_price).desc()
            )
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        total_value = sum(row.total_value for row in rows) or Decimal(1)
        
        return [
            {
                "category": row.category or "Uncategorized",
                "total_value": float(row.total_value or 0),
                "percentage": float((row.total_value / total_value) * 100),
                "item_count": row.item_count or 0,
                "total_stock": float(row.total_stock or 0),
            }
            for row in rows
        ]

    # ----------------------------------------------------------------------
    # Recent Stock Movements
    # ----------------------------------------------------------------------
    async def get_recent_movements(self, limit: int = 10) -> list[dict]:
        """Get recent stock movements."""
        stmt = (
            select(
                InventoryStockMovement.id,
                InventoryStockMovement.type,
                InventoryStockMovement.quantity,
                InventoryStockMovement.previous_stock,
                InventoryStockMovement.new_stock,
                InventoryStockMovement.reference_type,
                InventoryStockMovement.reference_id,
                InventoryStockMovement.note,
                InventoryStockMovement.performed_by,
                InventoryItem.name.label("item_name"),
                InventoryItem.unit.label("unit"),
                InventoryStockMovement.created_at,
            )
            .join(InventoryItem, InventoryStockMovement.item_id == InventoryItem.id)
            .order_by(InventoryStockMovement.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        # Map movement types to display names
        type_map = {
            StockMovementType.PURCHASE: "Purchase",
            StockMovementType.SALE: "Sale",
            StockMovementType.RETURN: "Return",
            StockMovementType.ADJUSTMENT: "Adjustment",
            StockMovementType.USAGE: "Usage",
            StockMovementType.TRANSFER: "Transfer",
            StockMovementType.WASTE: "Waste",
        }
        
        return [
            {
                "id": str(row.id),
                "type": row.type,
                "display_type": type_map.get(row.type, row.type),
                "quantity": float(row.quantity),
                "previous_stock": float(row.previous_stock),
                "new_stock": float(row.new_stock),
                "item_name": row.item_name,
                "unit": row.unit,
                "reference_type": row.reference_type,
                "reference_id": str(row.reference_id) if row.reference_id else None,
                "note": row.note,
                "performed_by": row.performed_by,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    # ----------------------------------------------------------------------
    # Usage per Project
    # ----------------------------------------------------------------------
    async def get_usage_by_project(self, project_id: UUID) -> list[dict]:
        """Get material usage for a specific project."""
        stmt = (
            select(
                InventoryMaterialUsage.id,
                InventoryMaterialUsage.quantity,
                InventoryMaterialUsage.total_cost,
                InventoryMaterialUsage.note,
                InventoryMaterialUsage.created_at,
                InventoryItem.id.label("item_id"),
                InventoryItem.name.label("item_name"),
                InventoryItem.category.label("item_category"),
                InventoryItem.unit.label("unit"),
                InventoryItem.cost_price.label("unit_cost"),
            )
            .join(InventoryItem, InventoryMaterialUsage.item_id == InventoryItem.id)
            .where(InventoryMaterialUsage.project_id == project_id)
            .order_by(InventoryMaterialUsage.created_at.desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        return [
            {
                "usage_id": str(row.id),
                "item_id": str(row.item_id),
                "item_name": row.item_name,
                "item_category": row.item_category,
                "unit": row.unit,
                "quantity": float(row.quantity),
                "unit_cost": float(row.unit_cost or 0),
                "total_cost": float(row.total_cost or 0),
                "note": row.note,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def get_project_usage_summary(self, project_id: UUID) -> dict:
        """Get summary of material usage for a project."""
        usages = await self.get_usage_by_project(project_id)
        
        total_items = len(usages)
        total_quantity = sum(u["quantity"] for u in usages)
        total_cost = sum(u["total_cost"] for u in usages)
        
        # Group by category
        by_category = {}
        for u in usages:
            category = u["item_category"] or "Uncategorized"
            if category not in by_category:
                by_category[category] = {
                    "quantity": 0,
                    "cost": 0,
                    "items": 0
                }
            by_category[category]["quantity"] += u["quantity"]
            by_category[category]["cost"] += u["total_cost"]
            by_category[category]["items"] += 1
        
        return {
            "total_items": total_items,
            "total_quantity": total_quantity,
            "total_cost": total_cost,
            "by_category": by_category,
            "items": usages
        }

    # ----------------------------------------------------------------------
    # Usage by Workshop Job
    # ----------------------------------------------------------------------
    async def get_usage_by_job(self, job_id: UUID) -> list[dict]:
        """Get material usage for a specific workshop job."""
        stmt = (
            select(
                InventoryMaterialUsage.id,
                InventoryMaterialUsage.quantity,
                InventoryMaterialUsage.total_cost,
                InventoryMaterialUsage.note,
                InventoryMaterialUsage.created_at,
                InventoryItem.id.label("item_id"),
                InventoryItem.name.label("item_name"),
                InventoryItem.category.label("item_category"),
                InventoryItem.unit.label("unit"),
                InventoryItem.cost_price.label("unit_cost"),
            )
            .join(InventoryItem, InventoryMaterialUsage.item_id == InventoryItem.id)
            .where(InventoryMaterialUsage.job_id == job_id)
            .order_by(InventoryMaterialUsage.created_at.desc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        return [
            {
                "usage_id": str(row.id),
                "item_id": str(row.item_id),
                "item_name": row.item_name,
                "item_category": row.item_category,
                "unit": row.unit,
                "quantity": float(row.quantity),
                "unit_cost": float(row.unit_cost or 0),
                "total_cost": float(row.total_cost or 0),
                "note": row.note,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    # ----------------------------------------------------------------------
    # Inventory Turnover
    # ----------------------------------------------------------------------
    async def get_turnover_rate(self, days: int = 30) -> dict:
        """Calculate inventory turnover rate."""
        since = datetime.now() - timedelta(days=days)
        
        # Total usage cost in period
        usage_cost = await self.db.scalar(
            select(func.coalesce(func.sum(InventoryMaterialUsage.total_cost), Decimal(0)))
            .where(InventoryMaterialUsage.created_at >= since)
        ) or Decimal(0)
        
        # Average inventory value in period
        avg_inventory = await self.db.scalar(
            select(func.coalesce(func.avg(InventoryItem.current_stock * InventoryItem.cost_price), Decimal(1)))
            .where(InventoryItem.status == InventoryStatus.ACTIVE)
        ) or Decimal(1)
        
        turnover = usage_cost / avg_inventory if avg_inventory else Decimal(0)
        
        # Calculate days of inventory
        daily_usage = usage_cost / days if days > 0 else Decimal(0)
        days_of_inventory = avg_inventory / daily_usage if daily_usage else Decimal(0)
        
        return {
            "turnover_rate": float(turnover),
            "days_of_inventory": float(days_of_inventory),
            "period_days": days,
            "usage_cost": float(usage_cost),
            "avg_inventory_value": float(avg_inventory),
        }

    # ----------------------------------------------------------------------
    # Stock Movement Analytics
    # ----------------------------------------------------------------------
    async def get_movement_analytics(self, days: int = 30) -> dict:
        """Get stock movement analytics for a period."""
        since = datetime.now() - timedelta(days=days)
        
        # Total in and out movements
        movement_stats = await self.db.execute(
            select(
                InventoryStockMovement.type,
                func.coalesce(func.sum(InventoryStockMovement.quantity), Decimal(0)).label("total_quantity"),
                func.count(InventoryStockMovement.id).label("count"),
            )
            .where(InventoryStockMovement.created_at >= since)
            .group_by(InventoryStockMovement.type)
        )
        rows = movement_stats.all()
        
        summary = {
            "in": {"quantity": 0, "count": 0},
            "out": {"quantity": 0, "count": 0},
            "adjustment": {"quantity": 0, "count": 0},
        }
        
        for row in rows:
            if row.type in [StockMovementType.PURCHASE, StockMovementType.RETURN]:
                summary["in"]["quantity"] += float(row.total_quantity or 0)
                summary["in"]["count"] += row.count or 0
            elif row.type in [StockMovementType.SALE, StockMovementType.USAGE, StockMovementType.WASTE]:
                summary["out"]["quantity"] += float(row.total_quantity or 0)
                summary["out"]["count"] += row.count or 0
            else:
                summary["adjustment"]["quantity"] += float(row.total_quantity or 0)
                summary["adjustment"]["count"] += row.count or 0
        
        # Calculate net change
        net_change = summary["in"]["quantity"] - summary["out"]["quantity"]
        
        return {
            "period_days": days,
            "summary": summary,
            "net_change": net_change,
            "movement_count": sum(row.count or 0 for row in rows),
        }

    # ----------------------------------------------------------------------
    # Cost Analysis
    # ----------------------------------------------------------------------
    async def get_cost_analysis(self) -> dict:
        """Get inventory cost analysis."""
        # Total inventory value
        total_value = await self.db.scalar(
            select(func.coalesce(func.sum(InventoryItem.current_stock * InventoryItem.cost_price), Decimal(0)))
            .where(InventoryItem.status == InventoryStatus.ACTIVE)
        ) or Decimal(0)
        
        # Cost by category
        cost_by_category = await self.db.execute(
            select(
                InventoryItem.category,
                func.coalesce(func.sum(InventoryItem.current_stock * InventoryItem.cost_price), Decimal(0)).label("value"),
                func.count(InventoryItem.id).label("count"),
            )
            .where(InventoryItem.status == InventoryStatus.ACTIVE)
            .group_by(InventoryItem.category)
            .order_by(func.sum(InventoryItem.current_stock * InventoryItem.cost_price).desc())
        )
        categories = cost_by_category.all()
        
        # Average cost per item
        avg_cost = await self.db.scalar(
            select(func.coalesce(func.avg(InventoryItem.cost_price), Decimal(0)))
            .where(InventoryItem.status == InventoryStatus.ACTIVE)
        ) or Decimal(0)
        
        # Most expensive items
        expensive_items = await self.db.execute(
            select(
                InventoryItem.id,
                InventoryItem.name,
                InventoryItem.category,
                InventoryItem.cost_price,
                InventoryItem.current_stock,
                (InventoryItem.current_stock * InventoryItem.cost_price).label("total_value"),
            )
            .where(InventoryItem.status == InventoryStatus.ACTIVE)
            .order_by((InventoryItem.current_stock * InventoryItem.cost_price).desc())
            .limit(10)
        )
        
        return {
            "total_value": float(total_value),
            "average_cost": float(avg_cost),
            "by_category": [
                {
                    "category": row.category or "Uncategorized",
                    "value": float(row.value or 0),
                    "percentage": float((row.value / total_value) * 100) if total_value else 0,
                    "count": row.count or 0,
                }
                for row in categories
            ],
            "most_expensive": [
                {
                    "id": str(row.id),
                    "name": row.name,
                    "category": row.category,
                    "cost_price": float(row.cost_price),
                    "current_stock": float(row.current_stock),
                    "total_value": float(row.total_value or 0),
                }
                for row in expensive_items
            ],
        }

    # ----------------------------------------------------------------------
    # Quick Actions / Recommendations
    # ----------------------------------------------------------------------
    async def get_recommendations(self) -> list[dict]:
        """Generate inventory recommendations."""
        recommendations = []
        
        # Check low stock
        low_stock_items = await self.get_stock_alerts()
        if low_stock_items:
            critical = [i for i in low_stock_items if i["severity"] == "critical"]
            if critical:
                recommendations.append({
                    "type": "reorder",
                    "priority": "high",
                    "message": f"{len(critical)} items are critically low on stock and need immediate reorder.",
                    "items": critical[:5],
                })
            else:
                recommendations.append({
                    "type": "reorder",
                    "priority": "medium",
                    "message": f"{len(low_stock_items)} items are running low on stock.",
                    "items": low_stock_items[:5],
                })
        
        # Check inventory value
        value_analysis = await self.get_cost_analysis()
        if value_analysis["total_value"] > 100000000:  # 100M IDR
            recommendations.append({
                "type": "value_alert",
                "priority": "medium",
                "message": f"Inventory value is {value_analysis['total_value']:,.0f} IDR. Consider reviewing slow-moving items.",
                "items": value_analysis["most_expensive"][:3],
            })
        
        # Check turnover
        turnover = await self.get_turnover_rate(30)
        if turnover["turnover_rate"] < 1:
            recommendations.append({
                "type": "turnover",
                "priority": "medium",
                "message": f"Inventory turnover rate is {turnover['turnover_rate']:.1f}x. Consider reducing stock levels.",
                "items": [],
            })
        
        return recommendations

    # ----------------------------------------------------------------------
    # Export Data
    # ----------------------------------------------------------------------
    async def get_export_data(self) -> dict:
        """Get all inventory data for export."""
        items = await self.db.execute(
            select(
                InventoryItem.id,
                InventoryItem.name,
                InventoryItem.category,
                InventoryItem.unit,
                InventoryItem.cost_price,
                InventoryItem.selling_price,
                InventoryItem.current_stock,
                InventoryItem.min_stock_threshold,
                InventoryItem.max_stock_threshold,
                InventoryItem.status,
                InventoryItem.sku,
                InventoryItem.barcode,
                InventoryItem.location,
                InventoryItem.created_at,
            )
            .order_by(InventoryItem.category, InventoryItem.name)
        )
        
        return {
            "items": [
                {
                    "id": str(row.id),
                    "name": row.name,
                    "category": row.category,
                    "unit": row.unit,
                    "cost_price": float(row.cost_price),
                    "selling_price": float(row.selling_price),
                    "current_stock": float(row.current_stock),
                    "min_stock_threshold": float(row.min_stock_threshold),
                    "max_stock_threshold": float(row.max_stock_threshold),
                    "status": row.status,
                    "sku": row.sku,
                    "barcode": row.barcode,
                    "location": row.location,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in items
            ],
            "exported_at": datetime.now().isoformat(),
        }