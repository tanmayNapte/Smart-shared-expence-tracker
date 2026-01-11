from functools import wraps
from flask import session, redirect
from models import db, User

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return view(*args, **kwargs)
    return wrapper


def admin_only(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")

        user = db.session.get(User, session["user_id"])
        if not user or user.role != "admin":
            return "Forbidden", 403

        return view(*args, **kwargs)
    return wrapper
