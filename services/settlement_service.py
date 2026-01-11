
from models import db, Settlement
from services.group_service import is_user_member
from services.group_service import InvalidGroupDataError


class SettlementNotFoundError(Exception):
    """Raised when a settlement is not found"""
    pass


class InvalidSettlementDataError(Exception):
    """Raised when settlement data is invalid"""
    pass


class GroupNotFoundError(Exception):
    """Raised when a group is not found"""
    pass

class SettlementPermissionError(Exception):
    pass


def create_settlement(group_id, payer_id, receiver_id, amount, actor_id):

    # 🔒 PERMISSION CHECK (FIRST)
    if actor_id != payer_id and actor_id != receiver_id:
        raise SettlementPermissionError(
            "You can only record a settlement if you are the payer or the receiver."
        )

    # ---------- VALIDATION ----------
    if not all([group_id, payer_id, receiver_id, amount]):
        raise InvalidSettlementDataError("All fields are required")

    if payer_id == receiver_id:
        raise InvalidSettlementDataError("Payer and receiver cannot be the same")

    if amount <= 0:
        raise InvalidSettlementDataError("Amount must be positive")

    # ---------- GROUP CHECK ----------
    from services.group_service import get_group_by_id
    try:
        get_group_by_id(group_id)
    except Exception:
        raise GroupNotFoundError(f"Group {group_id} not found")

    # ---------- CREATE ----------
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

def record_settlement(group_id, payer_id, receiver_id, amount, actor_id):
    # Basic sanity
    if payer_id == receiver_id:
        raise InvalidGroupDataError("Payer and receiver cannot be same")

    if amount <= 0:
        raise InvalidGroupDataError("Invalid settlement amount")

    # 🔒 CRITICAL RULE
    if actor_id != payer_id and actor_id != receiver_id:
        raise SettlementPermissionError("Forbidden")

    # Optional but recommended: group membership check
    if not is_user_member(group_id, payer_id) or not is_user_member(group_id, receiver_id):
        raise SettlementPermissionError("User not in group")

    settlement = Settlement(
        group_id=group_id,
        payer_id=payer_id,
        receiver_id=receiver_id,
        amount=amount
    )

    db.session.add(settlement)
    db.session.commit()

    return settlement