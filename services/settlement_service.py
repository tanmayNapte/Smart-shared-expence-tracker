"""
Settlement Service - Business logic for settlement operations

Rules:
- No Flask (request, session, redirect, flash)
- No decorators
- Can use models and db
- Can raise exceptions
- Returns plain Python data
"""
from models import db, Settlement


class SettlementNotFoundError(Exception):
    """Raised when a settlement is not found"""
    pass


class InvalidSettlementDataError(Exception):
    """Raised when settlement data is invalid"""
    pass


class GroupNotFoundError(Exception):
    """Raised when a group is not found"""
    pass


def create_settlement(group_id, payer_id, receiver_id, amount):
    """
    Create a settlement record.
    
    Args:
        group_id: Group ID
        payer_id: User ID who is paying
        receiver_id: User ID who is receiving
        amount: Settlement amount (float)
    
    Returns:
        Settlement object
    
    Raises:
        InvalidSettlementDataError: If data is invalid
        GroupNotFoundError: If group doesn't exist
    """
    if not all([group_id, payer_id, receiver_id, amount]):
        raise InvalidSettlementDataError("All fields are required")
    
    if payer_id == receiver_id:
        raise InvalidSettlementDataError("Payer and receiver cannot be the same")
    
    if amount <= 0:
        raise InvalidSettlementDataError("Amount must be positive")
    
    # Validate group exists
    from services.group_service import get_group_by_id
    try:
        get_group_by_id(group_id)
    except Exception:
        raise GroupNotFoundError(f"Group {group_id} not found")
    
    settlement = Settlement(
        group_id=int(group_id),
        payer_id=int(payer_id),
        receiver_id=int(receiver_id),
        amount=float(amount)
    )
    
    db.session.add(settlement)
    db.session.commit()
    return settlement


def get_settlement_by_id(settlement_id):
    """
    Get a settlement by ID.
    
    Args:
        settlement_id: Settlement ID
    
    Returns:
        Settlement object or None
    
    Raises:
        SettlementNotFoundError: If settlement doesn't exist
    """
    settlement = Settlement.query.get(settlement_id)
    if not settlement:
        raise SettlementNotFoundError(f"Settlement {settlement_id} not found")
    return settlement


def get_group_settlements(group_id):
    """
    Get all settlements for a group.
    
    Args:
        group_id: Group ID
    
    Returns:
        List of Settlement objects ordered by created_at desc
    """
    return Settlement.query.filter_by(
        group_id=group_id
    ).order_by(Settlement.created_at.desc()).all()
