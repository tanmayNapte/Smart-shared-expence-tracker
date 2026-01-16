from flask import Blueprint, jsonify, render_template, request, redirect, session
from werkzeug.security import generate_password_hash
from sqlalchemy import func

from models import db, User
from models import Expense, GroupMember


from services.ledger_service import get_user_net_balances_by_person
from utils.decorators import admin_only, login_required

users_bp = Blueprint("users", __name__)


@users_bp.route("/api/users")
def api_users():
    users = User.query.all()
    return jsonify([
        {"id": u.id, "name": u.name, "email": u.email}
        for u in users
    ])


@users_bp.route("/admin/create-user", methods=["GET", "POST"])
@admin_only
def create_user():
    if request.method == "POST":
        if User.query.filter_by(email=request.form["email"]).first():
            return render_template("create_user.html", error="User exists")

        user = User(
            name=request.form["name"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"])
        )

        db.session.add(user)
        db.session.commit()
        return redirect("/dashboard")

    return render_template("create_user.html")


@users_bp.route("/profile")
@login_required
def profile_page():
    user_id = session["user_id"]

    # 1) Groups count (how many groups you are part of)
    groups_count = GroupMember.query.filter_by(user_id=user_id).count()

    # 2) Expenses count (how many expenses you created)
    expenses_count = Expense.query.filter_by(created_by=user_id).count()

    # 3) Total paid by you
    total_paid = db.session.query(func.coalesce(func.sum(Expense.amount), 0)) \
        .filter(Expense.paid_by == user_id).scalar()

    # 4) Total spent (expenses you created) - optional but good stat
    total_spent = db.session.query(func.coalesce(func.sum(Expense.amount), 0)) \
        .filter(Expense.created_by == user_id).scalar()

    # 5) Net balances (owe vs owed)
    net_list = get_user_net_balances_by_person(user_id)

    total_you_owe = 0
    total_you_are_owed = 0

    for row in net_list:
    # row might be dict like {"person_id": 2, "name": "A", "amount": -120}
        amt = row.get("amount", 0)

        if amt < 0:
            total_you_owe += abs(amt)
        elif amt > 0:
            total_you_are_owed += amt


    stats = {
        "groups_count": groups_count,
        "expenses_count": expenses_count,
        "total_paid": float(total_paid or 0),
        "total_spent": float(total_spent or 0),
        "total_you_owe": float(total_you_owe),
        "total_you_are_owed": float(total_you_are_owed),
    }

    return render_template("profile.html", stats=stats)
