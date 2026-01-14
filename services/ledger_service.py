from collections import defaultdict
from models import Expense, ExpenseSplit, Settlement, User, Group


def get_user_net_balances_by_person(user_id):
    """
    Returns net balances per person PER GROUP.

    amount < 0  -> user owes that person
    amount > 0  -> that person owes user
    """

    from collections import defaultdict

    # (other_user_id, group_id) → amount
    net = defaultdict(float)

    # 1️⃣ Expenses YOU paid → others owe you
    paid_expenses = Expense.query.filter_by(paid_by=user_id).all()

    for expense in paid_expenses:
        for split in expense.splits:
            if split.user_id != user_id:
                key = (split.user_id, expense.group_id)
                net[key] += split.amount

    # 2️⃣ Expenses OTHERS paid → you owe them
    owed_splits = (
        ExpenseSplit.query
        .join(Expense)
        .filter(
            ExpenseSplit.user_id == user_id,
            Expense.paid_by != user_id
        )
        .all()
    )

    for split in owed_splits:
        key = (split.expense.paid_by, split.expense.group_id)
        net[key] -= split.amount

    # 3️⃣ Apply settlements (⚠️ group-specific!)
    settlements = Settlement.query.filter(
        (Settlement.payer_id == user_id) |
        (Settlement.receiver_id == user_id)
    ).all()

    for s in settlements:
        key = (
            s.receiver_id if s.payer_id == user_id else s.payer_id,
            s.group_id
        )

        if s.payer_id == user_id:
            net[key] += s.amount
        else:
            net[key] -= s.amount

    if not net:
        return []

    # 4️⃣ Fetch users + groups in bulk
    user_ids = {uid for uid, _ in net.keys()}
    group_ids = {gid for _, gid in net.keys()}

    users = User.query.filter(User.id.in_(user_ids)).all()
    groups = Group.query.filter(Group.id.in_(group_ids)).all()

    user_map = {u.id: u for u in users}
    group_map = {g.id: g for g in groups}

    # 5️⃣ Build final result
    result = []

    for (uid, gid), amount in net.items():
        if abs(amount) > 0.01:
            result.append({
                "user_id": uid,
                "name": user_map[uid].name,
                "group_name": group_map[gid].name,
                "amount": round(amount, 2)
            })

    return result
