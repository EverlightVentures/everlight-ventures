"""
Auto-SKU Generation Service
Generates unique, deterministic SKUs for inventory items
"""
import hashlib
import re
from database import Session
from models import Item


class SKUGenerator:
    """Autonomous SKU generation - 1 SKU per item, no duplicates"""

    @staticmethod
    def generate_sku(tenant_id, item_name, category=None):
        """
        Generate unique SKU for an item

        Format: {CATEGORY_PREFIX}-{HASH}-{COUNTER}
        Example: COFFEE-A3B2-001

        Args:
            tenant_id: Tenant ID (for uniqueness scoping)
            item_name: Item name
            category: Item category (optional)

        Returns:
            Unique SKU string
        """
        db = Session()

        try:
            # Generate category prefix
            if category:
                # Take first 3-6 letters of category, uppercase
                prefix = re.sub(r'[^A-Z]', '', category.upper())[:6]
                if not prefix:
                    prefix = "ITEM"
            else:
                prefix = "ITEM"

            # Generate deterministic hash from item name
            name_clean = re.sub(r'[^a-zA-Z0-9]', '', item_name.lower())
            hash_obj = hashlib.md5(name_clean.encode())
            hash_short = hash_obj.hexdigest()[:4].upper()

            # Find next available counter for this prefix
            counter = 1
            while True:
                sku = f"{prefix}-{hash_short}-{counter:03d}"

                # Check if SKU already exists for this tenant
                existing = db.query(Item).filter_by(
                    tenant_id=tenant_id,
                    sku=sku
                ).first()

                if not existing:
                    return sku

                counter += 1

                # Safety limit
                if counter > 999:
                    # Use longer hash if we hit limit
                    hash_short = hash_obj.hexdigest()[:8].upper()
                    counter = 1

        finally:
            db.close()

    @staticmethod
    def validate_sku_unique(tenant_id, sku):
        """
        Check if SKU is unique within tenant

        Args:
            tenant_id: Tenant ID
            sku: SKU to check

        Returns:
            True if unique, False if duplicate
        """
        db = Session()

        try:
            existing = db.query(Item).filter_by(
                tenant_id=tenant_id,
                sku=sku
            ).first()

            return existing is None

        finally:
            db.close()

    @staticmethod
    def bulk_generate_skus(tenant_id, items_data):
        """
        Generate SKUs for multiple items at once

        Args:
            tenant_id: Tenant ID
            items_data: List of dicts with 'name' and 'category'

        Returns:
            List of dicts with added 'sku' field
        """
        results = []

        for item in items_data:
            sku = SKUGenerator.generate_sku(
                tenant_id=tenant_id,
                item_name=item.get('name', 'Unknown'),
                category=item.get('category')
            )

            results.append({
                **item,
                'sku': sku
            })

        return results

    @staticmethod
    def generate_variant_sku(parent_sku, variant_name):
        """
        Generate SKU for item variant

        Format: {PARENT_SKU}-{VARIANT_CODE}
        Example: COFFEE-A3B2-001-LG (for Large variant)

        Args:
            parent_sku: Parent item SKU
            variant_name: Variant name (Size, Color, etc.)

        Returns:
            Variant SKU string
        """
        # Take first 2 letters of variant name
        variant_code = re.sub(r'[^A-Z]', '', variant_name.upper())[:2]

        if not variant_code:
            variant_code = "V1"

        return f"{parent_sku}-{variant_code}"
