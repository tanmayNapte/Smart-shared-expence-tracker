
from flask import Blueprint, request, jsonify, redirect, flash
from utils.decorators import login_required
from services.settlement_service import (
    create_settlement,
    InvalidSettlementDataError,
    GroupNotFoundError
)

settlements_bp = Blueprint("settlements", __name__)

@settlements_bp.route("/api/settlements", methods=["POST"])
def api_add_settlement():
    data = request.json
    try:
        settlement = create_settlement(
            group_id=data["group_id"],
            payer_id=data["payer_id"],
            receiver_id=data["receiver_id"],
            amount=data["amount"]
        )
        return jsonify({"status": "recorded", "settlement_id": settlement.id})
    except (InvalidSettlementDataError, GroupNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to create settlement"}), 500


@settlements_bp.route("/settlements/add", methods=["POST"])
@login_required
def add_settlement():
    group_id = request.form.get("group_id")
    payer_id = request.form.get("payer_id")
    receiver_id = request.form.get("receiver_id")
    amount = request.form.get("amount")
    
    try:
        settlement = create_settlement(
            group_id=int(group_id),
            payer_id=int(payer_id),
            receiver_id=int(receiver_id),
            amount=float(amount)
        )
        flash("Settlement recorded successfully", "success")
        return redirect(f"/groups/{group_id}")
    except (InvalidSettlementDataError, GroupNotFoundError) as e:
        flash(str(e), "error")
        return redirect(f"/groups/{group_id}")
    except (ValueError, TypeError) as e:
        flash("Invalid input", "error")
        return redirect(f"/groups/{group_id}")
    except Exception as e:
        flash("Failed to record settlement", "error")
        return redirect(f"/groups/{group_id}")
