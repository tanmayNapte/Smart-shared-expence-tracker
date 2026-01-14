# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "expense_users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default="user")
    

class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("expense_users.id"))


class GroupMember(db.Model):
    __tablename__ = "group_members"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("expense_users.id"))


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    paid_by = db.Column(db.Integer, db.ForeignKey("expense_users.id"))
    created_by = db.Column(db.Integer, db.ForeignKey("expense_users.id"), nullable=True)
    last_edited_by = db.Column(db.Integer, db.ForeignKey("expense_users.id"), nullable=True)
    last_edited_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    group = db.relationship("Group", backref="expenses")
    payer = db.relationship("User", foreign_keys=[paid_by], backref="expenses_paid")


class ExpenseSplit(db.Model):
    __tablename__ = "expense_splits"
    
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("expense_users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    
    # Add relationship to access expense data
    expense = db.relationship("Expense", backref="splits")


class Settlement(db.Model):
    __tablename__ = "settlements"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"))
    payer_id = db.Column(db.Integer, db.ForeignKey("expense_users.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("expense_users.id"))
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    group = db.relationship("Group")
    payer = db.relationship("User", foreign_keys=[payer_id], backref="settlements_paid")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="settlements_received")