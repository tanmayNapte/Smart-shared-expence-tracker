from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask import session, redirect, request, url_for

from models import db, User, Group, GroupMember, Expense, ExpenseSplit, Settlement


def is_admin():
    user_id = session.get("user_id")
    if not user_id:
        return False

    user = db.session.get(User, user_id)
    return user and user.role == "admin"


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return is_admin()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.login_page", next=request.url))


class AdminOnlyModelView(ModelView):
    def is_accessible(self):
        return is_admin()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.login_page", next=request.url))


# -------------------- USER --------------------
class UserAdminView(AdminOnlyModelView):
    column_exclude_list = ["password"]
    form_excluded_columns = ["password"]

    can_delete = False

    column_list = ["id", "name", "email", "role"]
    column_searchable_list = ["name", "email"]
    column_filters = ["role"]
    column_default_sort = ("id", True)


# -------------------- GROUP --------------------
class GroupAdminView(AdminOnlyModelView):
    column_list = ["id", "name", "created_by"]
    column_searchable_list = ["name"]
    column_filters = ["created_by"]
    column_default_sort = ("id", True)


# -------------------- GROUP MEMBER --------------------
class GroupMemberAdminView(AdminOnlyModelView):
    column_list = ["id", "group_id", "user_id"]
    column_filters = ["group_id", "user_id"]
    column_default_sort = ("id", True)


# -------------------- EXPENSE --------------------
class ExpenseAdminView(AdminOnlyModelView):
    column_list = [
        "id",
        "group_id",
        "amount",
        "description",
        "paid_by",
        "created_by",
        "last_edited_by",
        "created_at",
    ]
    column_searchable_list = ["description"]
    column_filters = ["group_id", "paid_by", "created_by", "last_edited_by"]
    column_default_sort = ("id", True)


# -------------------- EXPENSE SPLIT --------------------
class ExpenseSplitAdminView(AdminOnlyModelView):
    can_create = False
    can_edit = False
    can_delete = False

    column_list = ["id", "expense_id", "user_id", "amount"]
    column_filters = ["expense_id", "user_id"]
    column_default_sort = ("id", True)


# -------------------- SETTLEMENT --------------------
class SettlementAdminView(AdminOnlyModelView):
    column_list = ["id", "group_id", "payer_id", "receiver_id", "amount", "created_at"]
    column_filters = ["group_id", "payer_id", "receiver_id"]
    column_default_sort = ("id", True)


def setup_admin(app):
    admin = Admin(app, name="Ledger Admin", index_view=MyAdminIndexView())

    admin.add_view(UserAdminView(User, db.session))
    admin.add_view(GroupAdminView(Group, db.session))
    admin.add_view(GroupMemberAdminView(GroupMember, db.session))
    admin.add_view(ExpenseAdminView(Expense, db.session))
    admin.add_view(ExpenseSplitAdminView(ExpenseSplit, db.session))
    admin.add_view(SettlementAdminView(Settlement, db.session))

    return admin
