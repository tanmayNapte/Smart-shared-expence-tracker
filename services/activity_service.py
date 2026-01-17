from sqlalchemy import or_
from models import Expense, Settlement, User, Group

def get_activity_feed(user_id, limit=10):
    """
    Mixes Expenses + Settlements into one feed sorted by time.
    """

    # Fetch recent expenses where user involved
    expenses = (
        Expense.query
        .filter(or_(Expense.created_by == user_id, Expense.paid_by == user_id))
        .order_by(Expense.id.desc())
        .limit(limit)
        .all()
    )

    # Fetch recent settlements where user involved
    settlements = (
        Settlement.query
        .filter(or_(Settlement.payer_id == user_id, Settlement.receiver_id == user_id))
        .order_by(Settlement.id.desc())
        .limit(limit)
        .all()
    )

    feed = []

    # Expenses
    for e in expenses:
        group_name = "Unknown"
        if getattr(e, "group_id", None):
            g = Group.query.get(e.group_id)
            if g:
                group_name = g.name

        feed.append({
            "type": "expense",
            "id": e.id,
            "group_name": group_name,
            "amount": float(getattr(e, "amount", 0)),
            "title": getattr(e, "title", "Expense"),
        })

    # Settlements
    for s in settlements:
        group_name = "Unknown"
        if getattr(s, "group_id", None):
            g = Group.query.get(s.group_id)
            if g:
                group_name = g.name

        payer = User.query.get(s.payer_id)
        receiver = User.query.get(s.receiver_id)

        feed.append({
            "type": "settlement",
            "id": s.id,
            "group_name": group_name,
            "amount": float(s.amount),
            "payer_name": payer.name if payer else "Unknown",
            "receiver_name": receiver.name if receiver else "Unknown",
        })

    # Sort by newest id (works even if you don't have created_at)
    feed.sort(key=lambda x: x["id"], reverse=True)

    return feed[:limit]
