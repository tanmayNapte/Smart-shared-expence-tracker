"""
Group Service - Business logic for group operations

Rules:
- No Flask (request, session, redirect, flash)
- No decorators
- Can use models and db
- Can raise exceptions
- Returns plain Python data
"""
from models import db, Group, GroupMember, User, Expense, ExpenseSplit, Settlement
from sqlalchemy.orm import joinedload


class GroupNotFoundError(Exception):
    """Raised when a group is not found"""
    pass


class UserNotMemberError(Exception):
    """Raised when a user is not a member of a group"""
    pass


class InvalidGroupDataError(Exception):
    """Raised when group data is invalid"""
    pass


def create_group(name, created_by_id, member_ids=None):
    """
    Create a new group with members.
    
    Args:
        name: Group name
        created_by_id: ID of user creating the group
        member_ids: List of user IDs to add as members (optional)
    
    Returns:
        Group object
    
    Raises:
        InvalidGroupDataError: If name is empty or None
    """
    if not name or not name.strip():
        raise InvalidGroupDataError("Group name is required")
    
    group = Group(name=name.strip(), created_by=created_by_id)
    db.session.add(group)
    db.session.commit()
    
    # Add creator as member
    db.session.add(GroupMember(group_id=group.id, user_id=created_by_id))
    
    # Add other members if provided
    if member_ids:
        for user_id in member_ids:
            if user_id != created_by_id:  # Don't add creator twice
                # Check if user exists
                if User.query.get(user_id):
                    db.session.add(GroupMember(group_id=group.id, user_id=user_id))
    
    db.session.commit()
    return group


def get_user_groups(user_id):
    """
    Get all groups a user is a member of.
    
    Args:
        user_id: User ID
    
    Returns:
        List of Group objects
    """
    groups = (
        db.session.query(Group)
        .join(GroupMember)
        .filter(GroupMember.user_id == user_id)
        .all()
    )
    return groups


def get_user_groups_with_counts(user_id):
    """
    Get all groups a user is a member of with member counts.
    
    Args:
        user_id: User ID
    
    Returns:
        List of dicts with keys: id, name, member_count
    """
    groups = get_user_groups(user_id)
    result = []
    
    for group in groups:
        member_count = GroupMember.query.filter_by(group_id=group.id).count()
        result.append({
            "id": group.id,
            "name": group.name,
            "member_count": member_count
        })
    
    return result


def get_group_by_id(group_id):
    """
    Get a group by ID.
    
    Args:
        group_id: Group ID
    
    Returns:
        Group object or None
    
    Raises:
        GroupNotFoundError: If group doesn't exist
    """
    group = Group.query.get(group_id)
    if not group:
        raise GroupNotFoundError(f"Group {group_id} not found")
    return group


def rename_group_with_permission(group_id, user_id, new_name):
    if not new_name or not new_name.strip():
        raise InvalidGroupDataError("Group name cannot be empty")

    group = get_group_by_id(group_id)
    user = User.query.get(user_id)

    if not user:
        raise PermissionError("Invalid user")

    if not (group.created_by == user_id or user.role == "admin"):
        raise PermissionError("Forbidden")

    group.name = new_name.strip()
    db.session.commit()

    return group


def is_user_member(group_id, user_id):
    """
    Check if a user is a member of a group.
    
    Args:
        group_id: Group ID
        user_id: User ID
    
    Returns:
        bool
    """
    return GroupMember.query.filter_by(
        group_id=group_id, 
        user_id=user_id
    ).first() is not None


def get_group_members(group_id):
    """
    Get all members of a group.
    
    Args:
        group_id: Group ID
    
    Returns:
        List of User objects
    
    Raises:
        GroupNotFoundError: If group doesn't exist
    """
    get_group_by_id(group_id)  # Validate group exists
    
    members = (
        db.session.query(User)
        .join(GroupMember)
        .filter(GroupMember.group_id == group_id)
        .all()
    )
    return members


def add_members_to_group(group_id, user_ids):
    """
    Add users to a group.
    
    Args:
        group_id: Group ID
        user_ids: List of user IDs to add
    
    Returns:
        Number of members added
    
    Raises:
        GroupNotFoundError: If group doesn't exist
    """
    get_group_by_id(group_id)  # Validate group exists
    
    added_count = 0
    for user_id in user_ids:
        # Check if user exists
        if not User.query.get(user_id):
            continue
        
        # Check if already a member
        existing = GroupMember.query.filter_by(
            group_id=group_id, 
            user_id=user_id
        ).first()
        
        if not existing:
            db.session.add(GroupMember(group_id=group_id, user_id=user_id))
            added_count += 1
    
    db.session.commit()
    return added_count


def get_users_not_in_group(group_id):
    """
    Get all users who are not members of a group.
    
    Args:
        group_id: Group ID
    
    Returns:
        List of User objects
    """
    existing_member_ids = [
        m.user_id for m in GroupMember.query.filter_by(group_id=group_id).all()
    ]
    
    if existing_member_ids:
        users = User.query.filter(~User.id.in_(existing_member_ids)).all()
    else:
        users = User.query.all()
    
    return users


def _delete_group_internal(group):
    ExpenseSplit.query.filter(
        ExpenseSplit.expense_id.in_(
            db.session.query(Expense.id).filter_by(group_id=group.id)
        )
    ).delete(synchronize_session=False)

    Expense.query.filter_by(group_id=group.id).delete()
    Settlement.query.filter_by(group_id=group.id).delete()
    GroupMember.query.filter_by(group_id=group.id).delete()

    db.session.delete(group)
    db.session.commit()


def delete_group_with_permission(group_id, user_id):
    group = get_group_by_id(group_id)
    user = User.query.get(user_id)

    if not user:
        raise PermissionError("Invalid user")

    if not (group.created_by == user_id or user.role == "admin"):
        raise PermissionError("Forbidden")

    _delete_group_internal(group)



def calculate_balances(group_id):
    """
    Calculate balances for all members in a group.
    
    Args:
        group_id: Group ID
    
    Returns:
        Dict mapping user_id to balance (float)
        Positive balance = user is owed money
        Negative balance = user owes money
    
    Raises:
        GroupNotFoundError: If group doesn't exist
    """
    get_group_by_id(group_id)  # Validate group exists
    
    balances = {}
    
    # Initialize all members with zero balance
    members = GroupMember.query.filter_by(group_id=group_id).all()
    for member in members:
        balances[member.user_id] = 0.0
    
    # Add expenses paid
    expenses = Expense.query.filter_by(group_id=group_id).all()
    for expense in expenses:
        balances[expense.paid_by] += expense.amount
    
    # Subtract expense splits (what each person owes)
    for expense in expenses:
        splits = ExpenseSplit.query.filter_by(expense_id=expense.id).all()
        for split in splits:
            balances[split.user_id] -= split.amount_owed
    
    # Apply settlements
    settlements = Settlement.query.filter_by(group_id=group_id).all()
    for settlement in settlements:
        balances[settlement.payer_id] += settlement.amount
        balances[settlement.receiver_id] -= settlement.amount
    
    return balances


def balance_integrity_ok(balances):
    """
    Check if balances sum to zero (within tolerance).
    
    Args:
        balances: Dict mapping user_id to balance
    
    Returns:
        bool: True if balances are balanced
    """
    total = sum(balances.values())
    return abs(total) < 0.01


def suggest_settlements(group_id):
    """
    Suggest optimal settlements to balance accounts.
    
    Uses a greedy algorithm to minimize number of transactions.
    
    Args:
        group_id: Group ID
    
    Returns:
        List of dicts with keys: from, to, amount
    
    Raises:
        GroupNotFoundError: If group doesn't exist
    """
    balances = calculate_balances(group_id)
    
    creditors = []  # People who are owed money (positive balance)
    debtors = []     # People who owe money (negative balance)
    
    for user_id, balance in balances.items():
        if balance > 0.01:
            creditors.append([user_id, balance])
        elif balance < -0.01:
            debtors.append([user_id, -balance])  # Store as positive for easier calculation
    
    # Sort by amount (largest first)
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    
    suggestions = []
    i = j = 0
    
    # Greedy matching: match largest debtor with largest creditor
    while i < len(debtors) and j < len(creditors):
        debtor_id, debtor_amount = debtors[i]
        creditor_id, creditor_amount = creditors[j]
        
        settle_amount = min(debtor_amount, creditor_amount)
        
        suggestions.append({
            "from": debtor_id,
            "to": creditor_id,
            "amount": round(settle_amount, 2)
        })
        
        # Update remaining amounts
        debtors[i][1] -= settle_amount
        creditors[j][1] -= settle_amount
        
        # Move to next if fully settled
        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1
    
    return suggestions


def get_group_display_data(group_id, current_user_id):
    """
    Get all data needed to display a group page.
    
    Args:
        group_id: Group ID
    
    Returns:
        Dict with keys: group, members, expenses, balances, settlements, suggestions
    
    Raises:
        GroupNotFoundError: If group doesn't exist
    """
    group = get_group_by_id(group_id)
    user = User.query.get(current_user_id)

    can_manage = False
    if user and (group.created_by == user.id or user.role == "admin"):
        can_manage = True

    members = get_group_members(group_id)

    
    # Get expenses
    expenses = Expense.query.filter_by(
        group_id=group_id
    ).order_by(Expense.created_at.desc()).all()
    
    # Format expenses with payer names
    expenses_list = []
    for expense in expenses:
        payer = User.query.get(expense.paid_by)
        expenses_list.append({
            "id": expense.id,
            "amount": expense.amount,
            "description": expense.description,
            "payer_name": payer.name if payer else "Unknown",
            "created_at": expense.created_at
        })
    
    # Get balances and format
    balances_dict = calculate_balances(group_id)
    balances_list = []
    for user_id, balance in balances_dict.items():
        user = User.query.get(user_id)
        if user:
            balances_list.append({
                "name": user.name,
                "balance": balance
            })
    
    # Get settlements with user names
    settlements = Settlement.query.filter_by(
        group_id=group_id
    ).order_by(Settlement.created_at.desc()).all()
    
    settlements_list = []
    for settlement in settlements:
        payer = User.query.get(settlement.payer_id)
        receiver = User.query.get(settlement.receiver_id)
        settlements_list.append({
            "id": settlement.id,
            "amount": settlement.amount,
            "payer_name": payer.name if payer else "Unknown",
            "receiver_name": receiver.name if receiver else "Unknown",
            "created_at": settlement.created_at
        })
    
    # Get settlement suggestions with user names
    suggestions_raw = suggest_settlements(group_id)
    suggestions_list = []
    for suggestion in suggestions_raw:
        from_user = User.query.get(suggestion["from"])
        to_user = User.query.get(suggestion["to"])
        suggestions_list.append({
            "from": suggestion["from"],
            "to": suggestion["to"],
            "from_name": from_user.name if from_user else "Unknown",
            "to_name": to_user.name if to_user else "Unknown",
            "amount": suggestion["amount"]
        })
    
    return {
        "group": group,
        "members": members,
        "expenses": expenses_list,
        "balances": balances_list,
        "settlements": settlements_list,
        "suggestions": suggestions_list,
        "can_manage": can_manage
    }

