
from flask import Blueprint, request, jsonify, redirect, flash, session
from utils.decorators import login_required
from services.settlement_service import (
    create_settlement,
    InvalidSettlementDataError,
    GroupNotFoundError,
    SettlementPermissionError
)

settlements_bp = Blueprint("settlements", __name__)

@settlements_bp.route("/api/settlements", methods=["POST"])
@login_required
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

    try:
        group_id = int(request.form.get("group_id"))
        payer_id = int(request.form.get("payer_id"))
        receiver_id = int(request.form.get("receiver_id"))
        amount = float(request.form.get("amount"))
    except (ValueError, TypeError):
        flash("Invalid input", "error")
        return redirect(f"/groups/{request.form.get('group_id')}")

    actor_id = session.get("user_id")

    try:
        create_settlement(
            group_id=group_id,
            payer_id=payer_id,
            receiver_id=receiver_id,
            amount=amount,
            actor_id=actor_id
        )
        flash("Settlement recorded successfully", "success")
        
    except SettlementPermissionError:
        flash(
            "You can only record a settlement if you are the payer or the receiver.",
            "error"
        )

    except (InvalidSettlementDataError, GroupNotFoundError) as e:
        flash(str(e), "error")

    except Exception as e:
        print("ACTUAL ERROR:", type(e), e)
        flash(str(e), "error")


    return redirect(f"/groups/{group_id}")
