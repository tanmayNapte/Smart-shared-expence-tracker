from flask import Blueprint, request, jsonify, session, redirect, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from utils.helpers import promote_first_user_to_admin

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def index():
    return redirect("/dashboard" if "user_id" in session else "/login")


@auth_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.json
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 400

    user = User(
        name=data["name"],
        email=data["email"],
        password=generate_password_hash(data["password"])
    )

    db.session.add(user)
    db.session.commit()
    return jsonify({"id": user.id, "name": user.name})


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()

    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = user.id
    return jsonify({"id": user.id, "name": user.name})


@auth_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid credentials", "error")
            return redirect("/login")

        session["user_id"] = user.id
        promote_first_user_to_admin()
        return redirect("/dashboard")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        email = request.form["email"]
        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="Email exists")

        user = User(
            name=request.form["name"],
            email=email,
            password=generate_password_hash(request.form["password"])
        )

        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
