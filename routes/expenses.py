from flask import Blueprint, request, jsonify, redirect, flash, session, render_template
from routes import settlements
from utils.decorators import login_required
from services.expense_service import (
    create_expense,
    edit_expense,
    delete_expense,
    get_expense_by_id,
    InvalidExpenseDataError,
    GroupNotFoundError,
    ExpenseNotFoundError,
    PermissionError
)
from models import Expense, Settlement, User, GroupMember
from sqlalchemy import desc


expenses_bp = Blueprint("expenses", __name__)

@expenses_bp.route("/api/expenses", methods=["POST"])
@login_required
def api_add_expense():
    data = request.json
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        splits = {int(uid): float(amt) for uid, amt in data.get("splits", {}).items()}
        expense = create_expense(
            group_id=data["group_id"],
            amount=data["amount"],
            paid_by=data["paid_by"],
            created_by=user_id,
            description=data.get("description"),
            splits=splits if splits else None
        )
        return jsonify({"status": "ok", "expense_id": expense.id})
    except (InvalidExpenseDataError, GroupNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to create expense"}), 500


@expenses_bp.route("/expenses/new", methods=["GET"])
@login_required
def new_expense_page():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
        
    group_id = request.args.get('group_id')
    try:
        if group_id:
            group_id = int(group_id)
    except:
        group_id = None

    try:
        from services.group_service import get_user_groups
        groups = get_user_groups(user_id)
        return render_template("create_expense.html", groups=groups, selected_group_id=group_id)
    except Exception as e:
        flash("Failed to load groups for expense creation", "error")
        return redirect("/dashboard")


@expenses_bp.route("/expenses/add", methods=["POST"])
@login_required
def add_expense():
    group_id = request.form.get("group_id")
    amount = request.form.get("amount")
    description = request.form.get("description", "")
    paid_by = request.form.get("paid_by")
    user_id = session.get("user_id")
    
    if not user_id:
        return redirect("/login")
    
    try:
        expense = create_expense(
            group_id=int(group_id),
            amount=float(amount),
            paid_by=int(paid_by),
            created_by=user_id,
            description=description if description else None,
            splits=None  # Will split equally
        )
        flash("Expense added successfully", "success")
        return redirect(f"/groups/{group_id}")
    except (InvalidExpenseDataError, GroupNotFoundError) as e:
        flash(str(e), "error")
        return redirect(f"/groups/{group_id}")
    except (ValueError, TypeError) as e:
        flash("Invalid input", "error")
        return redirect(f"/groups/{group_id}")
    except Exception as e:
        flash(f"Failed to add expense: {str(e)}", "error")
        return redirect(f"/groups/{group_id}")


@expenses_bp.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense_page(expense_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
    
    try:
        expense = get_expense_by_id(expense_id)
        
        if request.method == "POST":
            amount = request.form.get("amount")
            paid_by = request.form.get("paid_by")
            description = request.form.get("description", "")
            
            # Only update fields that were provided
            updated_expense = edit_expense(
                expense_id=expense_id,
                user_id=user_id,
                amount=float(amount) if amount else None,
                paid_by=int(paid_by) if paid_by else None,
                description=description if description else None
            )
            
            flash("Expense updated successfully", "success")
            return redirect(f"/groups/{expense.group_id}")
        
        # GET request - show edit form
        from services.group_service import get_group_members
        members = get_group_members(expense.group_id)
        
        return render_template("edit_expense.html", expense=expense, members=members)
        
    except ExpenseNotFoundError:
        flash("Expense not found", "error")
        return redirect("/dashboard")
    except PermissionError as e:
        flash(str(e), "error")
        try:
            expense = get_expense_by_id(expense_id)
            return redirect(f"/groups/{expense.group_id}")
        except:
            return redirect("/dashboard")
    except Exception as e:
        flash(f"Failed to edit expense: {str(e)}", "error")
        try:
            expense = get_expense_by_id(expense_id)
            return redirect(f"/groups/{expense.group_id}")
        except:
            return redirect("/dashboard")


@expenses_bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense_route(expense_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
    
    try:
        expense = get_expense_by_id(expense_id)
        group_id = expense.group_id
        
        delete_expense(expense_id=expense_id, user_id=user_id)
        flash("Expense deleted successfully", "success")
        return redirect(f"/groups/{group_id}")
        
    except ExpenseNotFoundError:
        flash("Expense not found", "error")
        return redirect("/dashboard")
    except PermissionError as e:
        flash(str(e), "error")
        try:
            expense = get_expense_by_id(expense_id)
            return redirect(f"/groups/{expense.group_id}")
        except:
            return redirect("/dashboard")
    except Exception as e:
        flash(f"Failed to delete expense: {str(e)}", "error")
        try:
            expense = get_expense_by_id(expense_id)
            return redirect(f"/groups/{expense.group_id}")
        except:
            return redirect("/dashboard")


# totals must come from FULL net_list (not only top 5)
@expenses_bp.route("/activity")
@login_required
def activity_page():
    filter_type = request.args.get("type", "all")  # all | expense | settlement
    activities = []

    # EXPENSE activities (SAFE)
    if filter_type in ["all", "expense"]:
        my_group_ids = [
            gm.group_id for gm in GroupMember.query.filter_by(user_id=session["user_id"]).all()
        ]

        expenses = Expense.query.filter(Expense.group_id.in_(my_group_ids)) \
            .order_by(Expense.id.desc()) \
            .limit(30) \
            .all()


        for e in expenses:
            paid_by_user = User.query.get(e.paid_by) if e.paid_by else None
            created_by_user = User.query.get(e.created_by) if e.created_by else None

            paid_by_name = paid_by_user.name if paid_by_user else "Unknown"
            created_by_name = created_by_user.name if created_by_user else "Unknown"

            activities.append({
                "type": "expense",
                "title": f"{paid_by_name} paid ₹{e.amount}",
                "subtitle": e.description or "Expense added",
                "meta": f"Created by {created_by_name}",
                "time": getattr(e, "created_at", None)
            })

    # For now settlements disabled until we confirm model fields
    # if filter_type in ["all", "settlement"]:
    #     settlements = Settlement.query.order_by(Settlement.id.desc()).limit(30).all()
    #     for s in settlements:
    #         activities.append({
    #             "type": "settlement",
    #             "title": f"Settlement ₹{s.amount}",
    #             "subtitle": "Settlement done",
    #             "meta": "Settlement",
    #             "time": getattr(s, "created_at", None)
    #         })

    activities.sort(key=lambda x: x["time"] or 0, reverse=True)

    return render_template("activity.html", activities=activities, filter_type=filter_type)
