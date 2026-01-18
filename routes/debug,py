from flask import Blueprint
from models import db

debug_bp = Blueprint("debug_bp", __name__)

@debug_bp.route("/_migrate_expenses_once")
def migrate_expenses_once():
    db.session.execute(db.text("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS created_by INTEGER;"))
    db.session.execute(db.text("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS last_edited_by INTEGER;"))
    db.session.execute(db.text("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS last_edited_at TIMESTAMP;"))
    db.session.commit()
    return "Migration done"
