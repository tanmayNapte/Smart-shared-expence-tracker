
from flask import Blueprint, request, jsonify, redirect, flash, session, render_template
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
            amount=data["amount"],
            actor_id=session.get("user_id")
        )
        return jsonify({"status": "recorded", "settlement_id": settlement.id})
    except (InvalidSettlementDataError, GroupNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to create settlement"}), 500

@settlements_bp.route("/settlements/new", methods=["GET"])
@login_required
def new_settlement_page():
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
        from models import User
        
        groups = get_user_groups(user_id)
        current_user = User.query.get(user_id)
        
        return render_template(
            "create_settlement.html", 
            groups=groups, 
            selected_group_id=group_id,
            current_user=current_user  # This was missing!
        )
    except Exception as e:
        print(f"ERROR: {e}")
        flash("Failed to load groups for settlement", "error")
        return redirect("/dashboard")

@settlements_bp.route("/settlements/add", methods=["POST"])
@login_required
def add_settlement():

    try:
        group_id = int(request.form.get("group_id"))
        payer_id = int(request.form.get("payer_id"))
        receiver_id = int(request.form.get("receiver_id"))
        amount = float(request.form.get("amount"))
    except (ValueError, TypeError):
        flash("Invalid input parameters", "error")
        gid = request.form.get('group_id')
        if gid and gid.isdigit():
            return redirect(f"/groups/{gid}")
        return redirect("/dashboard")

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
