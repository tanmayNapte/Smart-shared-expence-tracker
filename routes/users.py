from flask import Blueprint, jsonify, render_template, request, redirect, session
from werkzeug.security import generate_password_hash

from models import db, User
from utils.decorators import admin_only, login_required
from services.ledger_service import get_user_net_balances_by_person

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

    # this returns LIST in your project
    net_list = get_user_net_balances_by_person(user_id)

    owe_list = []
    owed_list = []

    # Split into owe / owed (Top 5 each)
    for row in net_list:
        amt = row.get("amount", 0)

        if amt < 0:
            owe_list.append({
                "name": row.get("name", "Unknown"),
                "amount": abs(float(amt)),
                "group_name": row.get("group_name", None),
            })
        elif amt > 0:
            owed_list.append({
                "name": row.get("name", "Unknown"),
                "amount": float(amt),
                "group_name": row.get("group_name", None),
            })

    # Sort big amounts first
# totals must come from FULL net_list (not only top 5)
        total_you_owe = 0
        total_you_are_owed = 0

        for row in net_list:
            amt = float(row.get("amount", 0))
            if amt < 0:
                total_you_owe += abs(amt)
            elif amt > 0:
                total_you_are_owed += amt

        net_position = total_you_are_owed - total_you_owe

        # only LIMIT lists for UI display
        owe_list = owe_list[:5]
        owed_list = owed_list[:5]


    stats = {
        "total_you_owe": float(total_you_owe),
        "total_you_are_owed": float(total_you_are_owed),
        "net_position": float(net_position),
    }

    return render_template(
        "profile.html",
        owe_list=owe_list,
        owed_list=owed_list,
        stats=stats
    )
