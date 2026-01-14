from flask import Blueprint, jsonify, render_template, request, redirect
from werkzeug.security import generate_password_hash
from models import db, User
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
    return render_template("profile.html")

