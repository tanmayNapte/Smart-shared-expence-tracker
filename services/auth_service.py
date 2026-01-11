from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User


def authenticate_user(email, password):
    """
    Authenticate user by email + password.
    Returns User object if valid, else None.
    """
    if not email or not password:
        return None

    user = User.query.filter_by(email=email).first()
    if not user:
        return None

    if not check_password_hash(user.password, password):
        return None

    return user


def create_user(name, email, password, role="user"):
    """
    Create a new user with hashed password.
    Raises ValueError if user already exists.
    """
    if User.query.filter_by(email=email).first():
        raise ValueError("User already exists")

    hashed_password = generate_password_hash(password)

    user = User(
        name=name,
        email=email,
        password=hashed_password,
        role=role
    )

    db.session.add(user)
    db.session.commit()
    return user


def get_user_by_session(session):
    """
    Fetch currently logged-in user from session.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def is_admin(user):
    """
    Check if given user is admin.
    """
    return user is not None and user.role == "admin"
