from flask import Blueprint, request, jsonify, session, render_template, redirect, flash
from models import db, User
from utils.decorators import login_required, admin_only
from services.group_service import (
    create_group,
    get_user_groups,
    get_group_members,
    calculate_balances,
    balance_integrity_ok,
    get_group_by_id,
    GroupNotFoundError,
    InvalidGroupDataError
)

groups_bp = Blueprint("groups", __name__)

@groups_bp.route("/api/groups", methods=["POST"])
@login_required
def api_create_group():
    data = request.json
    try:
        group = create_group(
            name=data["name"],
            created_by_id=data["creator_id"],
            member_ids=data.get("member_ids", [])
        )
        return jsonify({"group_id": group.id})
    except InvalidGroupDataError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to create group"}), 500


@groups_bp.route("/api/groups", methods=["GET"])
@login_required
def api_user_groups():
    try:
        user_id = session["user_id"]   # ← source of truth
        groups = get_user_groups(user_id)
        return jsonify([{"id": g.id, "name": g.name} for g in groups])
    except Exception:
        return jsonify({"error": "Failed to get groups"}), 500


@groups_bp.route("/api/groups/<int:group_id>/members")
@login_required
def api_group_members(group_id):
    try:
        members = get_group_members(group_id)
        return jsonify([{"id": u.id, "name": u.name} for u in members])
    except GroupNotFoundError:
        return jsonify({"error": "Group not found"}), 404
    except Exception as e:
        return jsonify({"error": "Failed to get members"}), 500


@groups_bp.route("/api/groups/<int:group_id>/balances")
@login_required
def api_balances(group_id):
    try:
        balances = calculate_balances(group_id)
        if not balance_integrity_ok(balances):
            return jsonify({"error": "Integrity violated"}), 500
        return jsonify(balances)
    except GroupNotFoundError:
        return jsonify({"error": "Group not found"}), 404
    except Exception as e:
        return jsonify({"error": "Failed to calculate balances"}), 500


@groups_bp.route("/dashboard")
@login_required
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")
    
    try:
        from services.group_service import get_user_groups_with_counts
        groups = get_user_groups_with_counts(user_id)
        total_balance = 0
        for g in groups:
            g["user_balance"] = g.get("user_balance", 0)
            total_balance += g["user_balance"]


        return render_template(
            "dashboard.html",
            groups=groups,
            total_balance=total_balance
        )
        
    except Exception as e:
        print("DASHBOARD LOAD ERROR:", type(e), e)
        flash("Failed to load groups", "error")
        return render_template(
            "dashboard.html",
            groups=[],
            total_balance=0
        )


@groups_bp.route("/groups/new", methods=["GET", "POST"])
@login_required
def create_group_page():
    users = User.query.all()  # ✅ defined once

    if request.method == "POST":
        name = request.form.get("name")
        member_ids = [
            int(uid) for uid in request.form.getlist("members")
            if uid.isdigit()
        ]

        try:
            user_id = session.get("user_id")
            if not user_id:
                return redirect("/login")
            
            group = create_group(
                name=name,
                created_by_id=user_id,
                member_ids=member_ids
            )
            flash("Group created successfully", "success")
            return redirect(f"/groups/{group.id}")

        except InvalidGroupDataError as e:
            flash(str(e), "error")
            return render_template(
                "create_group.html",
                users=users
            )
        except Exception as e:
            flash(f"Failed to create group: {str(e)}", "error")
            return render_template(
                "create_group.html",
                users=users
            )

    # ✅ GET request
    return render_template("create_group.html", users=users)


@groups_bp.route("/groups/<int:group_id>")
@login_required
def group_page(group_id):
    user_id = session.get("user_id")
    
    try:
        from services.group_service import (
            is_user_member,
            get_group_display_data,
            UserNotMemberError
        )
        
        # Check if user is a member
        if not is_user_member(group_id, user_id):
            flash("You don't have access to this group", "error")
            return redirect("/dashboard")
        
        # Get all display data
        data = get_group_display_data(group_id, user_id)
        
        return render_template(
            "group.html",
            group=data["group"],
            members=data["members"],
            expenses=data["expenses"],
            balances=data["balances"],
            settlements=data["settlements"],
            suggestions=data["suggestions"],
            can_manage=data["can_manage"]
        )
    except GroupNotFoundError:
        flash("Group not found", "error")
        return redirect("/dashboard")
    except Exception as e:
        flash("Failed to load group", "error")
        return redirect("/dashboard")


@groups_bp.route("/groups/<int:group_id>/members", methods=["GET", "POST"])
@login_required
@admin_only
def add_members_page(group_id):
    try:
        group = get_group_by_id(group_id)
        
        if request.method == "POST":
            from services.group_service import add_members_to_group
            member_ids = [int(uid) for uid in request.form.getlist("members") if uid.isdigit()]
            add_members_to_group(group_id, member_ids)
            flash("Members added successfully", "success")
            return redirect(f"/groups/{group_id}")
        
        # GET request - show form
        from services.group_service import get_users_not_in_group
        users = get_users_not_in_group(group_id)
        return render_template("add_members.html", group=group, users=users)
    except GroupNotFoundError:
        flash("Group not found", "error")
        return redirect("/dashboard")
    except Exception as e:
        flash("Failed to add members", "error")
        return redirect(f"/groups/{group_id}")


@groups_bp.route("/groups/<int:group_id>/rename", methods=["GET", "POST"])
@login_required
def rename_group_page(group_id):
    user_id = session.get("user_id")

    try:
        group = get_group_by_id(group_id)

        if request.method == "POST":
            new_name = request.form.get("name")

            from services.group_service import rename_group_with_permission
            rename_group_with_permission(group_id, user_id, new_name)

            flash("Group renamed successfully", "success")
            return redirect(f"/groups/{group_id}")

        # GET request
        return render_template("rename_group.html", group=group)

    except PermissionError:
        flash("You are not allowed to rename this group", "error")
        return redirect(f"/groups/{group_id}")

    except InvalidGroupDataError as e:
        return render_template(
            "rename_group.html",
            group=group,
            error=str(e)
        )

    except GroupNotFoundError:
        flash("Group not found", "error")
        return redirect("/dashboard")


@groups_bp.route("/groups/<int:group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id):
    try:
        user_id = session["user_id"]
        from services.group_service import delete_group_with_permission
        delete_group_with_permission(group_id, user_id)
        flash("Group deleted successfully", "success")
        return redirect("/dashboard")
    except PermissionError:
        flash("Not authorized to delete this group", "error")
        return redirect("/dashboard")

    