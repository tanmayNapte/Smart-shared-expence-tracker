from flask import Blueprint, request, jsonify, redirect, flash, session, render_template
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