"""
Expense Service - Business logic for expense operations

Rules:
- No Flask (request, session, redirect, flash)
- No decorators
- Can use models and db
- Can raise exceptions
- Returns plain Python data
"""
from models import db, Expense, ExpenseSplit, GroupMember


class ExpenseNotFoundError(Exception):
    """Raised when an expense is not found"""
    pass


class InvalidExpenseDataError(Exception):
    """Raised when expense data is invalid"""
    pass


class GroupNotFoundError(Exception):
    """Raised when a group is not found"""
    pass


def create_expense(group_id, amount, paid_by, description=None, splits=None):
    """
    Create an expense with splits.
    
    Args:
        group_id: Group ID
        amount: Expense amount (float)
        paid_by: User ID who paid
        description: Optional description
        splits: Dict mapping user_id to amount_owed (optional)
                If None, splits equally among all group members
    
    Returns:
        Expense object
    
    Raises:
        InvalidExpenseDataError: If data is invalid
        GroupNotFoundError: If group doesn't exist
    """
    if not group_id or not amount or not paid_by:
        raise InvalidExpenseDataError("group_id, amount, and paid_by are required")
    
    if amount <= 0:
        raise InvalidExpenseDataError("Amount must be positive")
    
    # Validate group exists
    from services.group_service import get_group_by_id
    try:
        get_group_by_id(group_id)
    except Exception:
        raise GroupNotFoundError(f"Group {group_id} not found")
    
    # Create expense
    expense = Expense(
        group_id=group_id,
        amount=float(amount),
        paid_by=int(paid_by),
        description=description.strip() if description else None
    )
    db.session.add(expense)
    db.session.commit()
    
    # Create splits
    if splits:
        # Use provided splits
        for user_id, amount_owed in splits.items():
            db.session.add(
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=int(user_id),
                    amount_owed=float(amount_owed)
                )
            )
    else:
        # Split equally among all group members
        members = GroupMember.query.filter_by(group_id=group_id).all()
        if not members:
            raise InvalidExpenseDataError("Group has no members")
        
        split_amount = amount / len(members)
        for member in members:
            db.session.add(
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=member.user_id,
                    amount_owed=split_amount
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
