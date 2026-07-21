# modules/price_list/services.py
from uuid import UUID
from typing import Optional, List, Tuple
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessError, NotFoundError, ValidationError
from core.constants import InquiryStatus
from .models import (
    PriceListItem,
    PriceListCategory,
    PriceListDiscount,
    PriceHistory,
    CustomPrice
)
from modules.price_list.repository import (
    PriceListRepository,
    PriceListCategoryRepository,
    PriceListDiscountRepository,
)
from .schemas import (
    PriceListItemCreate,
    PriceListItemUpdate,
    PriceListCategoryCreate,
    PriceListCategoryUpdate,
    PriceListDiscountCreate,
    PriceListDiscountUpdate,
    PriceListBulkUpdate,
    PriceChangeRequest,
    PriceRevertRequest,
    CustomPriceCreate,
    CustomPriceUpdate,
)


class PriceListService:
    """Service untuk Price List management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PriceListRepository(db)
        self.category_repo = PriceListCategoryRepository(db)
        self.discount_repo = PriceListDiscountRepository(db)

    # =========================================================================
    # PRICE LIST ITEMS - CRUD
    # =========================================================================

    async def create_item(self, data: PriceListItemCreate) -> PriceListItem:
        """
        Create a new price list item.
        
        Args:
            data: PriceListItemCreate schema
            
        Returns:
            Created PriceListItem
            
        Raises:
            ValidationError: If SKU already exists or validation fails
        """
        # Convert to dict
        item_data = data.model_dump()

        # Set effective date if not provided
        if not item_data.get('effective_date'):
            item_data['effective_date'] = date.today()

        # Check SKU uniqueness if provided
        if item_data.get('sku'):
            existing = await self.repo.get_by_sku(item_data['sku'])
            if existing:
                raise ValidationError(f"SKU '{item_data['sku']}' already exists")

        # Validate category exists
        if item_data.get('category'):
            category = await self.category_repo.get_by_name(item_data['category'])
            if not category:
                raise ValidationError(f"Category '{item_data['category']}' does not exist")

        # Create item
        item = PriceListItem(**item_data)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)

        # Add initial price history
        await self.repo.add_price_history({
            "item_id": item.id,
            "old_price": item.price,
            "new_price": item.price,
            "changed_by": item.created_by or "system",
            "reason": "Initial price creation"
        })

        await self.db.flush()
        return item

    async def get_item(self, item_id: UUID) -> Optional[PriceListItem]:
        """Get price list item by ID."""
        return await self.repo.get(item_id)

    async def get_item_with_details(self, item_id: UUID) -> Optional[PriceListItem]:
        """Get price list item with all related data."""
        return await self.repo.get_with_details(item_id)

    async def list_items(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        active_only: bool = True,
        vehicle_brand: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        include_deleted: bool = False,
        page: int = 1,
        limit: int = 10,
        sort_by: str = "name",
        sort_order: str = "asc"
    ) -> Tuple[List[PriceListItem], int]:
        """
        List price items with pagination and filters.
        
        Returns:
            Tuple of (items, total_count)
        """
        return await self.repo.list_paginated(
            category=category,
            search=search,
            active_only=active_only,
            vehicle_brand=vehicle_brand,
            vehicle_model=vehicle_model,
            include_deleted=include_deleted,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )

    async def update_item(
        self,
        item_id: UUID,
        data: PriceListItemUpdate
    ) -> Optional[PriceListItem]:
        """
        Update price list item.
        
        Args:
            item_id: ID of item to update
            data: Update data
            
        Returns:
            Updated PriceListItem
            
        Raises:
            NotFoundError: If item not found
            ValidationError: If validation fails
        """
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        # Validate SKU uniqueness if updating
        if data.sku and data.sku != item.sku:
            existing = await self.repo.get_by_sku(data.sku)
            if existing:
                raise ValidationError(f"SKU '{data.sku}' already exists")

        # Validate category if updating
        if data.category and data.category != item.category:
            category = await self.category_repo.get_by_name(data.category)
            if not category:
                raise ValidationError(f"Category '{data.category}' does not exist")

        # Set updated_by
        if data.updated_by:
            update_data["updated_by"] = data.updated_by
        else:
            update_data["updated_by"] = "system"

        # If price is changing, add price history
        if 'price' in update_data and update_data['price'] != item.price:
            old_price = item.price
            new_price = update_data['price']

            # Update item
            result = await self.repo.update(item_id, update_data)

            # Add price history
            await self.repo.add_price_history({
                "item_id": item_id,
                "old_price": old_price,
                "new_price": new_price,
                "changed_by": update_data["updated_by"],
                "reason": data.description or "Price update"
            })

            await self.db.flush()
            await self.db.refresh(result)
            return result

        return await self.repo.update(item_id, update_data)

    async def delete_item(self, item_id: UUID) -> bool:
        """
        Soft delete price list item.
        
        Args:
            item_id: ID of item to delete
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If item not found
            BusinessError: If item is used in active projects
        """
        return await self.repo.delete(item_id)

    async def hard_delete_item(self, item_id: UUID) -> bool:
        """
        Hard delete price list item (permanent).
        Warning: This cannot be undone!
        
        Args:
            item_id: ID of item to delete
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If item not found
        """
        return await self.repo.hard_delete(item_id)

    async def toggle_item(self, item_id: UUID) -> Optional[PriceListItem]:
        """
        Toggle active status of a price list item.
        
        Args:
            item_id: ID of item to toggle
            
        Returns:
            Updated PriceListItem
            
        Raises:
            NotFoundError: If item not found
        """
        item = await self.repo.toggle_active(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")
        return item

    # =========================================================================
    # PRICE MANAGEMENT
    # =========================================================================

    async def change_price(
        self,
        item_id: UUID,
        data: PriceChangeRequest,
        changed_by: str = "system"
    ) -> Optional[PriceListItem]:
        """
        Change price with history tracking.
        
        Args:
            item_id: ID of item
            data: Price change request
            changed_by: User making the change
            
        Returns:
            Updated PriceListItem
            
        Raises:
            NotFoundError: If item not found
            ValidationError: If price is invalid
        """
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        old_price = item.price
        new_price = data.new_price

        if old_price == new_price:
            raise ValidationError("New price must be different from current price")

        # Update price
        item.price = new_price
        await self.db.flush()

        # Add history
        await self.repo.add_price_history({
            "item_id": item_id,
            "old_price": old_price,
            "new_price": new_price,
            "changed_by": changed_by,
            "reason": data.reason
        })

        await self.db.refresh(item)
        return item

    async def revert_price(
        self,
        item_id: UUID,
        data: PriceRevertRequest,
        changed_by: str = "system"
    ) -> Optional[PriceListItem]:
        """
        Revert price to a historical price.
        
        Args:
            item_id: ID of item
            data: Revert request
            changed_by: User making the revert
            
        Returns:
            Updated PriceListItem
            
        Raises:
            NotFoundError: If item or history not found
            ValidationError: If history doesn't belong to item
        """
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        # Get history entry using the correct method
        history = await self.repo.get_price_history_entry(data.history_id)
        if not history:
            raise NotFoundError(f"Price history {data.history_id} not found")

        # Check if history belongs to this item
        if history.item_id != item_id:
            raise ValidationError("History entry does not belong to this item")

        old_price = item.price
        new_price = history.old_price

        if old_price == new_price:
            raise ValidationError("Price is already at the historical price")

        # Update price
        item.price = new_price
        await self.db.flush()

        # Add new history entry
        await self.repo.add_price_history({
            "item_id": item_id,
            "old_price": old_price,
            "new_price": new_price,
            "changed_by": changed_by,
            "reason": data.reason or f"Reverted to price from {history.changed_at.strftime('%Y-%m-%d %H:%M')}"
        })

        await self.db.refresh(item)
        return item

    async def get_price_history(self, item_id: UUID, limit: int = 50) -> List[PriceHistory]:
        """
        Get price history for an item.
        
        Args:
            item_id: ID of item
            limit: Max history entries to return
            
        Returns:
            List of PriceHistory entries
            
        Raises:
            NotFoundError: If item not found
        """
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        return await self.repo.get_price_history(item_id, limit)

    async def get_price_change_summary(self, item_id: UUID) -> dict:
        """
        Get price change summary for an item.
        
        Args:
            item_id: ID of item
            
        Returns:
            Price change summary dictionary
            
        Raises:
            NotFoundError: If item not found
        """
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        return await self.repo.get_price_change_summary(item_id)

    # =========================================================================
    # CATEGORY MANAGEMENT
    # =========================================================================

    async def create_category(self, data: PriceListCategoryCreate) -> PriceListCategory:
        """
        Create a new price list category.
        
        Args:
            data: Category creation data
            
        Returns:
            Created PriceListCategory
            
        Raises:
            ValidationError: If category name already exists
        """
        # Check if category already exists
        existing = await self.category_repo.get_by_name(data.name)
        if existing:
            raise ValidationError(f"Category '{data.name}' already exists")

        # Create category
        category_data = data.model_dump()
        category = PriceListCategory(**category_data)
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def get_category(self, category_id: UUID) -> Optional[PriceListCategory]:
        """Get category by ID."""
        return await self.category_repo.get(category_id)

    async def get_category_by_name(self, name: str) -> Optional[PriceListCategory]:
        """Get category by name."""
        return await self.category_repo.get_by_name(name)

    async def list_categories(self) -> List[PriceListCategory]:
        """List all active categories."""
        return await self.category_repo.list_active()

    async def get_categories(self) -> List[str]:
        """Get all unique category names."""
        return await self.repo.get_categories()

    async def get_categories_with_counts(self) -> List[dict]:
        """List categories with item counts."""
        return await self.category_repo.list_with_counts()

    async def update_category(
        self,
        category_id: UUID,
        data: PriceListCategoryUpdate
    ) -> Optional[PriceListCategory]:
        """
        Update a category.
        
        Args:
            category_id: ID of category
            data: Update data
            
        Returns:
            Updated PriceListCategory
            
        Raises:
            NotFoundError: If category not found
        """
        category = await self.category_repo.get(category_id)
        if not category:
            raise NotFoundError(f"Category {category_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        return await self.category_repo.update(category_id, update_data)

    async def delete_category(self, category_id: UUID) -> bool:
        """
        Delete a category.
        
        Args:
            category_id: ID of category
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If category not found
            ValidationError: If category has items
        """
        category = await self.category_repo.get(category_id)
        if not category:
            raise NotFoundError(f"Category {category_id} not found")

        # Check if category has items
        items = await self.repo.get_by_category(category.name)
        if items:
            raise ValidationError(
                f"Cannot delete category with {len(items)} items. "
                "Please reassign or delete the items first."
            )

        return await self.category_repo.delete(category_id)

    # =========================================================================
    # DISCOUNT MANAGEMENT
    # =========================================================================

    async def create_discount(self, data: PriceListDiscountCreate) -> PriceListDiscount:
        """
        Create a new discount.
        
        Args:
            data: Discount creation data
            
        Returns:
            Created PriceListDiscount
            
        Raises:
            ValidationError: If code already exists or dates invalid
        """
        # Check if code already exists
        existing = await self.discount_repo.get_by_code(data.code)
        if existing:
            raise ValidationError(f"Discount code '{data.code}' already exists")

        # Validate date range
        if data.valid_until and data.valid_from > data.valid_until:
            raise ValidationError("Valid from date must be before valid until date")

        # If applies_to_item_id is provided, validate item exists
        if data.applies_to_item_id:
            item = await self.repo.get(data.applies_to_item_id)
            if not item:
                raise ValidationError(f"Item {data.applies_to_item_id} not found")

        discount_data = data.model_dump()
        discount = PriceListDiscount(**discount_data)
        self.db.add(discount)
        await self.db.flush()
        await self.db.refresh(discount)
        return discount

    async def get_discount(self, discount_id: UUID) -> Optional[PriceListDiscount]:
        """Get discount by ID."""
        return await self.discount_repo.get(discount_id)

    async def get_discount_by_code(self, code: str) -> Optional[PriceListDiscount]:
        """Get discount by code."""
        return await self.discount_repo.get_by_code(code)

    async def list_discounts(self) -> List[PriceListDiscount]:
        """List all active discounts."""
        return await self.discount_repo.list_active()

    async def update_discount(
        self,
        discount_id: UUID,
        data: PriceListDiscountUpdate
    ) -> Optional[PriceListDiscount]:
        """
        Update a discount.
        
        Args:
            discount_id: ID of discount
            data: Update data
            
        Returns:
            Updated PriceListDiscount
            
        Raises:
            NotFoundError: If discount not found
            ValidationError: If validation fails
        """
        discount = await self.discount_repo.get(discount_id)
        if not discount:
            raise NotFoundError(f"Discount {discount_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        # Validate date range
        if 'valid_from' in update_data and 'valid_until' in update_data:
            if update_data['valid_from'] > update_data['valid_until']:
                raise ValidationError("Valid from date must be before valid until date")

        # If applies_to_item_id is provided, validate item exists
        if 'applies_to_item_id' in update_data and update_data['applies_to_item_id']:
            item = await self.repo.get(update_data['applies_to_item_id'])
            if not item:
                raise ValidationError(f"Item {update_data['applies_to_item_id']} not found")

        return await self.discount_repo.update(discount_id, update_data)

    async def delete_discount(self, discount_id: UUID) -> bool:
        """
        Delete a discount.
        
        Args:
            discount_id: ID of discount
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If discount not found
        """
        discount = await self.discount_repo.get(discount_id)
        if not discount:
            raise NotFoundError(f"Discount {discount_id} not found")

        return await self.discount_repo.delete(discount_id)

    async def validate_discount(self, code: str) -> dict:
        """
        Validate a discount code.
        
        Args:
            code: Discount code to validate
            
        Returns:
            Validation result dictionary
            
        Raises:
            NotFoundError: If discount not found
            BusinessError: If discount is not valid
        """
        discount = await self.discount_repo.get_by_code(code)
        if not discount:
            raise NotFoundError(f"Discount code '{code}' not found")

        if not discount.is_valid:
            raise BusinessError(f"Discount code '{code}' is not valid")

        return {
            "valid": True,
            "id": str(discount.id),
            "code": discount.code,
            "name": discount.name,
            "description": discount.description,
            "discount_percentage": float(discount.discount_percentage),
            "discount_amount": float(discount.discount_amount) if discount.discount_amount else None,
            "remaining_uses": discount.remaining_uses,
            "applies_to_all": discount.applies_to_all,
            "applies_to_category": discount.applies_to_category,
            "applies_to_item_id": str(discount.applies_to_item_id) if discount.applies_to_item_id else None,
        }

    async def use_discount(self, discount_id: UUID) -> Optional[PriceListDiscount]:
        """
        Use a discount by ID.
        
        Args:
            discount_id: ID of discount
            
        Returns:
            Updated PriceListDiscount
            
        Raises:
            NotFoundError: If discount not found
            BusinessError: If discount is not valid
        """
        discount = await self.discount_repo.get(discount_id)
        if not discount:
            raise NotFoundError(f"Discount {discount_id} not found")

        if not discount.is_valid:
            raise BusinessError(f"Discount '{discount.code}' is not valid")

        discount.used_count += 1
        await self.db.flush()
        await self.db.refresh(discount)
        return discount

    async def get_applicable_discounts(
        self,
        category: Optional[str] = None,
        item_id: Optional[UUID] = None
    ) -> List[PriceListDiscount]:
        """
        Get discounts applicable to a specific item or category.
        
        Args:
            category: Category name
            item_id: Item ID
            
        Returns:
            List of applicable discounts
        """
        return await self.discount_repo.get_applicable_discounts(category, item_id)

    # =========================================================================
    # CUSTOM PRICE MANAGEMENT
    # =========================================================================

    async def create_custom_price(
        self,
        data: CustomPriceCreate,
        created_by: str = "system"
    ) -> CustomPrice:
        """
        Create custom price.
        
        Args:
            data: Custom price creation data
            created_by: User creating the custom price
            
        Returns:
            Created CustomPrice
            
        Raises:
            NotFoundError: If item not found
            ValidationError: If validation fails
        """
        # Validate item exists
        item = await self.repo.get(data.item_id)
        if not item:
            raise NotFoundError(f"Price item {data.item_id} not found")

        # Validate if customer or project is provided
        if not data.customer_id and not data.project_id:
            raise ValidationError("Either customer_id or project_id must be provided")

        # Validate date range
        if data.valid_until and data.valid_from > data.valid_until:
            raise ValidationError("Valid from date must be before valid until date")

        custom_price_data = data.model_dump()
        custom_price_data["created_by"] = created_by

        return await self.repo.create_custom_price(custom_price_data)

    async def get_custom_prices(self, item_id: UUID) -> List[CustomPrice]:
        """
        Get all custom prices for an item.
        
        Args:
            item_id: ID of item
            
        Returns:
            List of CustomPrice
            
        Raises:
            NotFoundError: If item not found
        """
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        return await self.repo.get_custom_prices(item_id)

    async def get_custom_price(
        self,
        item_id: UUID,
        customer_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None
    ) -> Optional[CustomPrice]:
        """
        Get custom price for customer/project.
        
        Args:
            item_id: ID of item
            customer_id: ID of customer
            project_id: ID of project
            
        Returns:
            CustomPrice if found, None otherwise
        """
        return await self.repo.get_custom_price(item_id, customer_id, project_id)

    async def update_custom_price(
        self,
        custom_price_id: UUID,
        data: CustomPriceUpdate
    ) -> Optional[CustomPrice]:
        """
        Update custom price.
        
        Args:
            custom_price_id: ID of custom price
            data: Update data
            
        Returns:
            Updated CustomPrice
            
        Raises:
            NotFoundError: If custom price not found
            ValidationError: If validation fails
        """
        update_data = data.model_dump(exclude_unset=True)

        # Validate date range
        if 'valid_from' in update_data and 'valid_until' in update_data:
            if update_data['valid_from'] > update_data['valid_until']:
                raise ValidationError("Valid from date must be before valid until date")

        result = await self.repo.update_custom_price(custom_price_id, update_data)
        if not result:
            raise NotFoundError(f"Custom price {custom_price_id} not found")
        return result

    async def delete_custom_price(self, custom_price_id: UUID) -> bool:
        """
        Delete custom price.
        
        Args:
            custom_price_id: ID of custom price
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If custom price not found
        """
        return await self.repo.delete_custom_price(custom_price_id)

    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================

    async def bulk_create(self, items: List[PriceListItemCreate]) -> List[PriceListItem]:
        """
        Bulk create price list items.
        
        Args:
            items: List of item creation data
            
        Returns:
            List of created PriceListItem
            
        Raises:
            ValidationError: If validation fails
        """
        item_dicts = []
        for item_data in items:
            if not item_data.effective_date:
                item_data.effective_date = date.today()

            # Validate category exists
            if item_data.category:
                category = await self.category_repo.get_by_name(item_data.category)
                if not category:
                    raise ValidationError(f"Category '{item_data.category}' does not exist")

            item_dicts.append(item_data.model_dump())

        return await self.repo.bulk_create(item_dicts)

    async def bulk_update_prices(
        self,
        data: PriceListBulkUpdate
    ) -> int:
        """
        Bulk update prices by percentage.
        
        Args:
            data: Bulk update data
            
        Returns:
            Number of items updated
            
        Raises:
            ValidationError: If category not found
        """
        # Validate category exists
        category = await self.category_repo.get_by_name(data.category)
        if not category:
            raise ValidationError(f"Category '{data.category}' does not exist")

        return await self.repo.bulk_update_prices(
            category=data.category,
            percentage=data.percentage,
            vehicle_brand=data.vehicle_brand
        )

    
    async def remove_project_item(self, project_item_id: UUID) -> bool:
        """
        Remove price list item from project.
        
        Args:
            project_item_id: ID of project price list item
            
        Returns:
            True if removed
            
        Raises:
            NotFoundError: If item not found
        """
        return await self.repo.remove_project_item(project_item_id)

    # =========================================================================
    # STATISTICS
    # =========================================================================

    async def get_stats(self) -> dict:
        """
        Get price list statistics.
        
        Returns:
            Statistics dictionary
        """
        active_items = await self.repo.get_active_count()
        categories = await self.repo.get_categories()
        discounts = await self.discount_repo.list_active()

        # Get category counts
        category_counts = await self.repo.get_by_category_with_counts()

        return {
            "total_active_items": active_items,
            "total_categories": len(categories),
            "categories": categories,
            "category_counts": category_counts,
            "total_discounts": len(discounts) if discounts else 0,
            "active_discounts": len([d for d in (discounts or []) if d.is_active]),
            "total_price_items": await self.repo.count(),
        }

    # =========================================================================
    # PRICE CALCULATION HELPERS
    # =========================================================================

    async def calculate_price(
        self,
        item_id: UUID,
        quantity: Decimal = Decimal(1),
        customer_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        discount_code: Optional[str] = None
    ) -> dict:
        """
        Calculate final price with all applicable discounts.
        
        Args:
            item_id: ID of item
            quantity: Quantity
            customer_id: Customer ID (for custom pricing)
            project_id: Project ID (for custom pricing)
            discount_code: Discount code
            
        Returns:
            Price calculation result
        """
        # Get base item
        item = await self.repo.get(item_id)
        if not item:
            raise NotFoundError(f"Price item {item_id} not found")

        base_price = item.price
        subtotal = base_price * quantity

        # Check for custom price
        custom_price = await self.repo.get_custom_price(item_id, customer_id, project_id)
        if custom_price:
            base_price = custom_price.custom_price
            subtotal = base_price * quantity

        # Get discount
        discount_amount = Decimal(0)
        discount_percentage = Decimal(0)
        discount_id = None

        if discount_code:
            discount = await self.discount_repo.get_by_code(discount_code)
            if discount and discount.is_valid:
                discount_id = discount.id
                discount_percentage = discount.discount_percentage
                if discount.discount_amount:
                    discount_amount = discount.discount_amount
                else:
                    discount_amount = subtotal * (discount_percentage / Decimal(100))

                # Cap discount at subtotal
                if discount_amount > subtotal:
                    discount_amount = subtotal

        final_price = subtotal - discount_amount

        return {
            "item_id": str(item.id),
            "item_name": item.name,
            "category": item.category,
            "base_price": float(base_price),
            "quantity": float(quantity),
            "subtotal": float(subtotal),
            "discount_percentage": float(discount_percentage),
            "discount_amount": float(discount_amount),
            "discount_code": discount_code,
            "discount_id": str(discount_id) if discount_id else None,
            "final_price": float(final_price),
            "is_taxable": item.is_taxable,
            "unit": item.unit,
        }