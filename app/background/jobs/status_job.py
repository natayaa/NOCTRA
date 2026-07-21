# app/background/jobs/status_jobs.py
"""
Status update jobs for orders and inventory.
"""

from datetime import datetime, timedelta
from sqlalchemy import update, and_, or_

from app.background.jobs.base_job import BaseJob
from app.core.logging import get_logger
from app.core.constants import DateTimeConstants

logger = get_logger(__name__)

# ==================== STATUS UPDATE JOBS ====================

class UpdateOrderStatusJob(BaseJob):
    """Update order statuses based on time"""
    
    def __init__(self):
        super().__init__("update_order_status")
    
    async def execute(self, **kwargs):
        session = await self.get_session()
        
        try:
            from app.modules.projects.models import Project
            from app.modules.projects.enums import ProjectStatus
            
            now = datetime.utcnow()
            updated_count = 0
            
            # Auto-complete orders that are in_progress but completed_date is passed
            # This depends on your actual business logic
            
            # Example: Auto-expire pending orders after 7 days
            cutoff = now - timedelta(days=7)
            
            # Update pending orders older than 7 days to expired
            result = await session.execute(
                update(Project)
                .where(
                    and_(
                        Project.status == ProjectStatus.PENDING,
                        Project.created_at < cutoff,
                        Project.is_active == True
                    )
                )
                .values(
                    status=ProjectStatus.EXPIRED,
                    updated_at=now
                )
            )
            
            updated_count += result.rowcount
            
            # Auto-complete completed orders after 3 days
            cutoff_complete = now - timedelta(days=3)
            
            # This depends on your business logic
            # You might want to move completed orders to "delivered" or "closed"
            
            await session.commit()
            
            logger.info(f"Updated {updated_count} order statuses")
            return {'updated_count': updated_count}
            
        except ImportError:
            logger.warning("Project model not found, skipping order status update")
            return {'updated_count': 0}

class UpdateInventoryStatusJob(BaseJob):
    """Update inventory statuses based on stock levels"""
    
    def __init__(self):
        super().__init__("update_inventory_status")
    
    async def execute(self, **kwargs):
        session = await self.get_session()
        
        try:
            from app.modules.inventory.models import Inventory
            from app.modules.inventory.enums import InventoryStatus
            
            now = datetime.utcnow()
            updated_count = 0
            
            # Update inventory status based on stock levels
            # This depends on your business logic and stock thresholds
            
            # Example: Mark as out of stock if quantity <= 0
            result = await session.execute(
                update(Inventory)
                .where(
                    and_(
                        Inventory.quantity <= 0,
                        Inventory.status != InventoryStatus.OUT_OF_STOCK
                    )
                )
                .values(
                    status=InventoryStatus.OUT_OF_STOCK,
                    updated_at=now
                )
            )
            
            updated_count += result.rowcount
            
            # Example: Mark as low stock if quantity <= threshold
            # You might have a threshold field
            threshold = 5  # Default threshold
            
            result = await session.execute(
                update(Inventory)
                .where(
                    and_(
                        Inventory.quantity > 0,
                        Inventory.quantity <= threshold,
                        Inventory.status != InventoryStatus.LOW_STOCK
                    )
                )
                .values(
                    status=InventoryStatus.LOW_STOCK,
                    updated_at=now
                )
            )
            
            updated_count += result.rowcount
            
            # Example: Mark as in stock if quantity > threshold
            result = await session.execute(
                update(Inventory)
                .where(
                    and_(
                        Inventory.quantity > threshold,
                        Inventory.status.in_([InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK])
                    )
                )
                .values(
                    status=InventoryStatus.IN_STOCK,
                    updated_at=now
                )
            )
            
            updated_count += result.rowcount
            
            await session.commit()
            
            logger.info(f"Updated {updated_count} inventory statuses")
            return {'updated_count': updated_count}
            
        except ImportError:
            logger.warning("Inventory model not found, skipping inventory status update")
            return {'updated_count': 0}

# ==================== JOB INSTANCES ====================

update_order_status_job = UpdateOrderStatusJob()
update_inventory_status_job = UpdateInventoryStatusJob()

# ==================== WRAPPER FUNCTIONS ====================

async def update_order_status(**kwargs):
    return await update_order_status_job.run(**kwargs)

async def update_inventory_status(**kwargs):
    return await update_inventory_status_job.run(**kwargs)

# ==================== EXPORTS ====================

__all__ = [
    'update_order_status',
    'update_inventory_status',
]