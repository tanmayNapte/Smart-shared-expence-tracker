"""
Expense Service - Business logic for expense operations

Rules:
- No Flask (request, session, redirect, flash)
- No decorators
- Can use models and db
- Can raise exceptions
- Returns plain Python data
"""
from models import db, Expense, ExpenseSplit, GroupMember, User
from datetime import datetime
from services.split_engine import SplitEngine
from models import ExpenseSplit, Settlement

class ExpenseNotFoundError(Exception):
    """Raised when an expense is not found"""
    pass


class InvalidExpenseDataError(Exception):
    """Raised when expense data is invalid"""
    pass


class GroupNotFoundError(Exception):
    """Raised when a group is not found"""
    pass


class PermissionError(Exception):
    """Raised when user doesn't have permission for an operation"""
    pass



def create_expense(group_id, amount, paid_by, created_by, description=None, splits=None, split_type="equal"):

    if splits:
        calculated_splits = SplitEngine.calculate(amount, split_type, splits)
    else:
        # equal split among group members
        members = GroupMember.query.filter_by(group_id=group_id).all()
        user_ids = [m.user_id for m in members]
        calculated_splits = SplitEngine.calculate(amount, "equal", user_ids)
        split_type = "equal"

    expense = Expense(
        group_id=group_id,
        amount=amount,
        paid_by=paid_by,
        created_by=created_by,
        description=description,
        split_type=split_type
    )

    db.session.add(expense)
    db.session.flush()

    for uid, amt in calculated_splits.items():
        db.session.add(
            ExpenseSplit(
                expense_id=expense.id,
                user_id=uid,
                amount=amt
            )
        )

    db.session.commit()
    return expense


def get_expense_by_id(expense_id):
    """
    Get an expense by ID.
    
    Args:
        expense_id: Expense ID
    
    Returns:
        Expense object or None
    
    Raises:
        ExpenseNotFoundError: If expense doesn't exist
    """
    expense = Expense.query.get(expense_id)
    if not expense:
        raise ExpenseNotFoundError(f"Expense {expense_id} not found")
    return expense


def get_group_expenses(group_id):
    """
    Get all expenses for a group.
    
    Args:
        group_id: Group ID
    
    Returns:
        List of Expense objects ordered by created_at desc
    """
    return Expense.query.filter_by(
        group_id=group_id
    ).order_by(Expense.created_at.desc()).all()


def edit_expense(expense_id, user_id, amount=None, paid_by=None, description=None, splits=None, split_type=None):

    expense = Expense.query.filter_by(id=expense_id, is_active=True).first()

    if not expense:
        raise ExpenseNotFoundError("Expense not found")

    # BLOCK edit if settlement exists
    settlement_exists = Settlement.query.filter_by(group_id=expense.group_id).first()
    if settlement_exists:
        raise InvalidExpenseDataError("Cannot edit expense after settlement")

    # deactivate old version
    expense.is_active = False

    new_amount = amount if amount else expense.amount
    new_paid_by = paid_by if paid_by else expense.paid_by
    new_description = description if description else expense.description
    new_split_type = split_type if split_type else expense.split_type

    if splits:
        calculated_splits = SplitEngine.calculate(new_amount, new_split_type, splits)
    else:
        members = GroupMember.query.filter_by(group_id=expense.group_id).all()
        user_ids = [m.user_id for m in members]
        calculated_splits = SplitEngine.calculate(new_amount, "equal", user_ids)
        new_split_type = "equal"

    new_expense = Expense(
        group_id=expense.group_id,
        amount=new_amount,
        paid_by=new_paid_by,
        description=new_description,
        created_by=expense.created_by,
        last_edited_by=user_id,
        last_edited_at=datetime.utcnow(),
        split_type=new_split_type,
        version=expense.version + 1
    )

    db.session.add(new_expense)
    db.session.flush()

    for uid, amt in calculated_splits.items():
        db.session.add(
            ExpenseSplit(
                expense_id=new_expense.id,
                user_id=uid,
                amount=amt
            )
        )

    db.session.commit()
    return new_expense



def delete_expense(expense_id, user_id):
    """
    Delete an expense.
    
    Rules:
    - Only the creator of the expense, group creator, or admin can delete
    - This will also delete all associated expense splits
    
    Args:
        expense_id: Expense ID
        user_id: User ID attempting to delete
    
    Returns:
        None
    
    Raises:
        ExpenseNotFoundError: If expense doesn't exist
        PermissionError: If user doesn't have permission
    """
    expense = get_expense_by_id(expense_id)
    user = User.query.get(user_id)
    
    if not user:
        raise PermissionError("Invalid user")
    
    # Check permission: creator, group creator, or admin
    from services.group_service import get_group_by_id
    group = get_group_by_id(expense.group_id)
    
    can_delete = (
        expense.created_by == user_id or
        user.role == "admin" or
        group.created_by == user_id
    )
    
    if not can_delete:
        raise PermissionError("You don't have permission to delete this expense")
    
    # Delete associated splits first
    ExpenseSplit.query.filter_by(expense_id=expense.id).delete()
    
    # Delete expense
    db.session.delete(expense)
    db.session.commit()
