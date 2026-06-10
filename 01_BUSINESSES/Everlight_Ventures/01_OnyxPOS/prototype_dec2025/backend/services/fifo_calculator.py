"""
FIFO/COGS Calculator Service
Handles First-In-First-Out inventory costing and lot allocation
"""
from datetime import datetime
from sqlalchemy import and_
from models_inventory_advanced import InventoryLot, TransactionItemLot


class FIFOCalculator:
    """
    FIFO (First-In-First-Out) inventory costing service
    Automatically allocates sales from oldest inventory lots first
    """

    @staticmethod
    def allocate_sale(db, tenant_id, item_id, quantity_needed):
        """
        Allocate inventory from lots using FIFO method

        Args:
            db: Database session
            tenant_id: Tenant ID
            item_id: Item ID to allocate
            quantity_needed: Quantity to allocate from lots

        Returns:
            tuple: (allocations, total_cogs, success)
            allocations: List of dicts with lot_id, quantity, cost_per_unit, total_cost
            total_cogs: Total cost of goods sold
            success: Boolean indicating if allocation was successful
        """
        # Get available lots ordered by received_date (FIFO)
        available_lots = db.query(InventoryLot).filter(
            and_(
                InventoryLot.tenant_id == tenant_id,
                InventoryLot.item_id == item_id,
                InventoryLot.quantity > 0
            )
        ).order_by(InventoryLot.received_date.asc()).all()

        if not available_lots:
            return [], 0, False

        # Check if we have enough total inventory
        total_available = sum(lot.quantity for lot in available_lots)
        if total_available < quantity_needed:
            return [], 0, False

        # Allocate from oldest lots first
        allocations = []
        remaining_quantity = quantity_needed
        total_cogs = 0

        for lot in available_lots:
            if remaining_quantity <= 0:
                break

            # Determine how much to take from this lot
            quantity_from_lot = min(lot.quantity, remaining_quantity)

            # Calculate cost for this allocation
            cost_per_unit = float(lot.cost_per_unit)
            allocation_cost = quantity_from_lot * cost_per_unit

            # Record allocation
            allocations.append({
                'lot_id': lot.id,
                'lot_number': lot.lot_number,
                'quantity': quantity_from_lot,
                'cost_per_unit': cost_per_unit,
                'total_cost': allocation_cost
            })

            # Update totals
            total_cogs += allocation_cost
            remaining_quantity -= quantity_from_lot

        return allocations, total_cogs, True

    @staticmethod
    def apply_allocation(db, allocations):
        """
        Apply FIFO allocation by reducing lot quantities
        Should be called after allocate_sale to commit the allocation

        Args:
            db: Database session
            allocations: List of allocation dicts from allocate_sale
        """
        for allocation in allocations:
            lot = db.query(InventoryLot).filter_by(id=allocation['lot_id']).first()
            if lot:
                lot.quantity -= allocation['quantity']
                db.add(lot)

    @staticmethod
    def record_transaction_lots(db, transaction_item_id, allocations):
        """
        Record which lots were used for a transaction item
        Creates audit trail in transaction_item_lots table

        Args:
            db: Database session
            transaction_item_id: ID of the transaction item
            allocations: List of allocation dicts from allocate_sale
        """
        for allocation in allocations:
            txn_lot = TransactionItemLot(
                transaction_item_id=transaction_item_id,
                lot_id=allocation['lot_id'],
                quantity_used=allocation['quantity'],
                cost_per_unit=allocation['cost_per_unit'],
                total_cost=allocation['total_cost']
            )
            db.add(txn_lot)

    @staticmethod
    def calculate_weighted_average_cost(db, tenant_id, item_id):
        """
        Calculate weighted average cost for an item across all lots
        Useful for reporting when FIFO detail isn't needed

        Args:
            db: Database session
            tenant_id: Tenant ID
            item_id: Item ID

        Returns:
            float: Weighted average cost per unit
        """
        lots = db.query(InventoryLot).filter(
            and_(
                InventoryLot.tenant_id == tenant_id,
                InventoryLot.item_id == item_id,
                InventoryLot.quantity > 0
            )
        ).all()

        if not lots:
            return 0.0

        total_quantity = sum(lot.quantity for lot in lots)
        total_cost = sum(lot.quantity * float(lot.cost_per_unit) for lot in lots)

        if total_quantity == 0:
            return 0.0

        return total_cost / total_quantity

    @staticmethod
    def get_lot_summary(db, tenant_id, item_id):
        """
        Get summary of all lots for an item

        Args:
            db: Database session
            tenant_id: Tenant ID
            item_id: Item ID

        Returns:
            dict: Summary with total_quantity, total_value, avg_cost, lot_count
        """
        lots = db.query(InventoryLot).filter(
            and_(
                InventoryLot.tenant_id == tenant_id,
                InventoryLot.item_id == item_id,
                InventoryLot.quantity > 0
            )
        ).all()

        total_quantity = sum(lot.quantity for lot in lots)
        total_value = sum(lot.quantity * float(lot.cost_per_unit) for lot in lots)
        avg_cost = total_value / total_quantity if total_quantity > 0 else 0.0

        return {
            'total_quantity': total_quantity,
            'total_value': round(total_value, 2),
            'avg_cost': round(avg_cost, 2),
            'lot_count': len(lots),
            'lots': [
                {
                    'lot_number': lot.lot_number,
                    'quantity': lot.quantity,
                    'cost_per_unit': float(lot.cost_per_unit),
                    'total_cost': lot.total_cost,
                    'received_date': lot.received_date.isoformat(),
                    'expiration_date': lot.expiration_date.isoformat() if lot.expiration_date else None
                }
                for lot in lots
            ]
        }

    @staticmethod
    def create_lot(db, tenant_id, item_id, lot_number, quantity, cost_per_unit,
                   received_date=None, expiration_date=None):
        """
        Create a new inventory lot

        Args:
            db: Database session
            tenant_id: Tenant ID
            item_id: Item ID
            lot_number: Lot/batch number
            quantity: Quantity in this lot
            cost_per_unit: Cost per unit for this lot
            received_date: When lot was received (defaults to now)
            expiration_date: Optional expiration date

        Returns:
            InventoryLot: Created lot object
        """
        lot = InventoryLot(
            tenant_id=tenant_id,
            item_id=item_id,
            lot_number=lot_number,
            quantity=quantity,
            cost_per_unit=cost_per_unit,
            received_date=received_date or datetime.utcnow(),
            expiration_date=expiration_date
        )
        db.add(lot)
        return lot
