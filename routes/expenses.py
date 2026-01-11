from flask import Blueprint, request, jsonify, redirect, flash
from utils.decorators import login_required
from services.expense_service import (
    create_expense,
    InvalidExpenseDataError,
    GroupNotFoundError
)

expenses_bp = Blueprint("expenses", __name__)

@expenses_bp.route("/api/expenses", methods=["POST"])
def api_add_expense():
    data = request.json
    try:
        splits = {int(uid): float(amt) for uid, amt in data.get("splits", {}).items()}
        expense = create_expense(
            group_id=data["group_id"],
            amount=data["amount"],
            paid_by=data["paid_by"],
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
    
    try:
        expense = create_expense(
            group_id=int(group_id),
            amount=float(amount),
            paid_by=int(paid_by),
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
        flash("Failed to add expense", "error")
        return redirect(f"/groups/{group_id}")