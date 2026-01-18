from sqlalchemy import or_
from datetime import datetime
from models import Expense, Settlement, User, Group, GroupMember

def get_activity_feed(user_id, limit=5):
    # get my groups
    my_group_ids = [
        gm.group_id
        for gm in GroupMember.query.filter_by(user_id=user_id).all()
    ]

    # recent expenses from my groups
    expenses = (
        Expense.query
        .filter(Expense.group_id.in_(my_group_ids))
        .order_by(Expense.id.desc())
        .limit(limit)
        .all()
    )

    # recent settlements where I'm involved
    settlements = (
        Settlement.query
        .filter(or_(Settlement.payer_id == user_id, Settlement.receiver_id == user_id))
        .order_by(Settlement.id.desc())
        .limit(limit)
        .all()
    )

    feed = []

    # expenses
    for e in expenses:
        g = Group.query.get(e.group_id) if e.group_id else None
        feed.append({
            "type": "expense",
            "group_name": g.name if g else "Unknown",
            "amount": float(e.amount),
            "title": e.description or "Expense",
            "time": getattr(e, "created_at", None),
        })

    # settlements
    for s in settlements:
        g = Group.query.get(s.group_id) if s.group_id else None
        payer = User.query.get(s.payer_id)
        receiver = User.query.get(s.receiver_id)

        feed.append({
            "type": "settlement",
            "group_name": g.name if g else "Unknown",
            "amount": float(s.amount),
            "payer_name": payer.name if payer else "Unknown",
            "receiver_name": receiver.name if receiver else "Unknown",
            "time": getattr(s, "created_at", None),
        })

    # sort by time (fallback)
    feed.sort(key=lambda x: x["time"] or datetime.min, reverse=True)
    return feed[:limit]
