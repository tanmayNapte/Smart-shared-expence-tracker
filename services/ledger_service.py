from collections import defaultdict
from models import Expense, ExpenseSplit, Settlement, User


def get_user_net_balances_by_person(user_id):
    """
    Returns net balances per person across all groups.

    amount < 0  -> user owes that person
    amount > 0  -> that person owes user
    """

    net = defaultdict(float)

    # 1️⃣ Expenses YOU paid → others owe you
    paid_expenses = Expense.query.filter_by(paid_by=user_id).all()  # ← Changed from paid_by_id

    for expense in paid_expenses:
        for split in expense.splits:
            if split.user_id != user_id:
                net[split.user_id] += split.amount  # ← Changed from amount_owed

    # 2️⃣ Expenses OTHERS paid → you owe them
    owed_splits = (
        ExpenseSplit.query
        .join(Expense)
        .filter(
            ExpenseSplit.user_id == user_id,
            Expense.paid_by != user_id  # ← Changed from paid_by_id
        )
        .all()
    )

    for split in owed_splits:
        net[split.expense.paid_by] -= split.amount  # ← Changed from paid_by_id and amount_owed

    # 3️⃣ Apply settlements
    settlements = Settlement.query.filter(
        (Settlement.payer_id == user_id) |
        (Settlement.receiver_id == user_id)
    ).all()

    for s in settlements:
        if s.payer_id == user_id:
            # you paid someone → you owe less
            net[s.receiver_id] += s.amount
        else:
            # someone paid you → they owe less
            net[s.payer_id] -= s.amount

    # 4️⃣ Fetch users in one query (avoid N+1)
    if not net:
        return []

    users = User.query.filter(User.id.in_(net.keys())).all()
    user_map = {u.id: u for u in users}

    # 5️⃣ Build final result
    result = []
    for uid, amount in net.items():
        if abs(amount) > 0.01:
            result.append({
                "user_id": uid,
                "name": user_map[uid].name,
                "amount": round(amount, 2)
            })

    return result