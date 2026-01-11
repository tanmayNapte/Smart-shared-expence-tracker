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


def create_expense(group_id, amount, paid_by, created_by, description=None, splits=None):
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
        created_by=int(created_by),
        description=description.strip() if description else None
    )
    db.session.add(expense)
    db.session.flush()  # Get expense.id before creating splits
    
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


def edit_expense(expense_id, user_id, amount=None, paid_by=None, description=None):
    """
    Edit an expense.
    
    Rules:
    - Only the creator of the expense or group admin can edit
    - If amount or paid_by changes, expense splits need to be recalculated
    
    Args:
        expense_id: Expense ID
        user_id: User ID attempting to edit
        amount: New amount (optional)
        paid_by: New payer ID (optional)
        description: New description (optional)
    
    Returns:
        Updated Expense object
    
    Raises:
        ExpenseNotFoundError: If expense doesn't exist
        PermissionError: If user doesn't have permission
        InvalidExpenseDataError: If data is invalid
    """
    expense = get_expense_by_id(expense_id)
    user = User.query.get(user_id)
    
    if not user:
        raise PermissionError("Invalid user")
    
    # Check permission: creator or admin
    from services.group_service import get_group_by_id
    group = get_group_by_id(expense.group_id)
    
    can_edit = (
        expense.created_by == user_id or
        user.role == "admin" or
        group.created_by == user_id
    )
    
    if not can_edit:
        raise PermissionError("You don't have permission to edit this expense")
    
    # Update fields
    need_recalculate_splits = False
    
    if amount is not None:
        if amount <= 0:
            raise InvalidExpenseDataError("Amount must be positive")
        if expense.amount != float(amount):
            expense.amount = float(amount)
            need_recalculate_splits = True
    
    if paid_by is not None:
        if expense.paid_by != int(paid_by):
            expense.paid_by = int(paid_by)
            # No need to recalculate splits if only payer changes
    
    if description is not None:
        expense.description = description.strip() if description else None
    
    # Recalculate splits if amount changed
    if need_recalculate_splits:
        # Delete existing splits
        ExpenseSplit.query.filter_by(expense_id=expense.id).delete()
        
        # Create new splits (equal split)
        members = GroupMember.query.filter_by(group_id=expense.group_id).all()
        if not members:
            raise InvalidExpenseDataError("Group has no members")
        
        split_amount = expense.amount / len(members)
        for member in members:
            db.session.add(
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=member.user_id,
                    amount_owed=split_amount
                )
            )
    
    # Update audit fields
    expense.last_edited_by = user_id
    expense.last_edited_at = datetime.utcnow()
    
    db.session.commit()
    return expense


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
