from flask import Blueprint
from models import db

debug_bp = Blueprint("debug_bp", __name__)

@debug_bp.route("/repair_db")
def repair_db():
    """
    Emergency route to add missing columns directly via SQL.
    Use this if 'flask db upgrade' is not working on production.
    """
    try:
        # List of columns to check and add
        # Note: 'IF NOT EXISTS' for ADD COLUMN is supported in PostgreSQL 9.6+
        queries = [
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'General' NOT NULL;",
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS split_type VARCHAR(20) DEFAULT 'equal';",
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;",
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS created_by INTEGER;",
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS last_edited_by INTEGER;",
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS last_edited_at TIMESTAMP;",
            "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
        ]
        
        for query in queries:
            db.session.execute(db.text(query))
        
        db.session.commit()
        return "✅ Database Repair Successful! All missing columns (category, split_type, version, is_active, etc.) have been added."
    except Exception as e:
        db.session.rollback()
        return f"❌ Database Repair Failed: {str(e)}"

@debug_bp.route("/_migrate_expenses_once")
def migrate_expenses_once():
    return "This route is deprecated. Please use /repair_db instead."
