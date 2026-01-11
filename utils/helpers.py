"""
General helper functions (non-domain specific utilities)

Note: Domain-specific business logic should be in services/
"""
from models import db, User
from sqlalchemy import select


def promote_first_user_to_admin():
    """
    Promote the first user in the system to admin role if no admin exists.
    This is a utility function for initial setup.
    """
    admin_exists = db.session.execute(
        select(User.id).where(User.role == "admin")
    ).first()

    if admin_exists:
        return

    first_user = db.session.execute(
        select(User).order_by(User.id)
    ).first()

    if first_user:
        first_user[0].role = "admin"
        db.session.commit()
