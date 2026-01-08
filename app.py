from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import os
from sqlalchemy import or_, select
from models import db, User, Group, GroupMember, Settlement, Expense, ExpenseSplit
from auth import login_required, admin_only

# --------------------------------------------------
# APP SETUP
# --------------------------------------------------

load_dotenv()

app = Flask(__name__)

# Logic to fix the database URI for production
uri = os.getenv("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

db.init_app(app)

# --------------------------------------------------
# CONTEXT PROCESSOR
# --------------------------------------------------

@app.context_processor
def inject_current_user():
    if "user_id" in session:
        user = db.session.get(User, session["user_id"])
        return {"current_user": user}
    return {"current_user": None}


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def admin_required():
    if "user_id" not in session:
        return False
    user = db.session.get(User, session["user_id"])
    return user and user.role == "admin"


def calculate_balances(group_id):
    balances = {}

    members = GroupMember.query.filter_by(group_id=group_id).all()
    for m in members:
        balances[m.user_id] = 0.0

    expenses = Expense.query.filter_by(group_id=group_id).all()
    for exp in expenses:
        balances[exp.paid_by] += exp.amount

        splits = ExpenseSplit.query.filter_by(expense_id=exp.id).all()
        for s in splits:
            balances[s.user_id] -= s.amount_owed

    settlements = Settlement.query.filter_by(group_id=group_id).all()
    for s in settlements:
        balances[s.payer_id] += s.amount
        balances[s.receiver_id] -= s.amount

    return balances


def balance_integrity_ok(balances):
    return abs(sum(balances.values())) < 0.01


def promote_first_user_to_admin():
    """Promote the first registered user to admin if no admin exists."""
    try:
        # Check if ANY admin exists
        admin_exists = db.session.execute(
            select(User.id).where(User.role == "admin")
        ).first()

        if admin_exists:
            return

        # Get the first user (oldest by ID)
        first_user = db.session.execute(
            select(User).order_by(User.id)
        ).first()

        if first_user:
            user = first_user[0]  # Extract user from result tuple
            user.role = "admin"
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error promoting user to admin: {e}")


def suggest_settlements(group_id):
    """Suggest optimal settlements to minimize transactions."""
    balances = calculate_balances(group_id)

    creditors = []
    debtors = []

    for user_id, balance in balances.items():
        if balance > 0.01:  # Small threshold to avoid floating point issues
            creditors.append([user_id, balance])
        elif balance < -0.01:
            debtors.append([user_id, -balance])

    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    suggestions = []

    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debtor_amt = debtors[i]
        creditor_id, creditor_amt = creditors[j]

        settle_amt = min(debtor_amt, creditor_amt)

        suggestions.append({
            "from": debtor_id,
            "to": creditor_id,
            "amount": round(settle_amt, 2)
        })

        debtors[i][1] -= settle_amt
        creditors[j][1] -= settle_amt

        if debtors[i][1] < 0.01:  # Essentially zero
            i += 1
        if creditors[j][1] < 0.01:  # Essentially zero
            j += 1

    return suggestions


# --------------------------------------------------
# AUTH API
# --------------------------------------------------

@app.route("/api/auth/register", methods=["POST"])
def register():
    try:
        data = request.json
        
        # Check if user already exists
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Email already registered"}), 400
        
        hashed = generate_password_hash(data["password"])

        user = User(
            name=data["name"],
            email=data["email"],
            password=hashed
        )

        db.session.add(user)
        db.session.commit()
        
        return jsonify({"id": user.id, "name": user.name, "email": user.email})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Registration failed"}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    try:
        data = request.json
        user = User.query.filter_by(email=data["email"]).first()

        if not user or not check_password_hash(user.password, data["password"]):
            return jsonify({"error": "Invalid credentials"}), 401

        # Set session for API login as well
        session["user_id"] = user.id
        
        return jsonify({"id": user.id, "name": user.name, "email": user.email})
    except Exception as e:
        return jsonify({"error": "Login failed"}), 500


# --------------------------------------------------
# USERS
# --------------------------------------------------

@app.route("/api/users")
def all_users():
    try:
        users = User.query.all()
        return jsonify([{"id": u.id, "name": u.name, "email": u.email} for u in users])
    except Exception as e:
        return jsonify({"error": "Failed to fetch users"}), 500


# --------------------------------------------------
# GROUPS
# --------------------------------------------------

@app.route("/api/groups", methods=["POST"])
def create_group():
    try:
        data = request.json
        group = Group(name=data["name"], created_by=data["creator_id"])
        db.session.add(group)
        db.session.commit()

        for uid in data["member_ids"]:
            db.session.add(GroupMember(group_id=group.id, user_id=uid))

        db.session.commit()
        return jsonify({"group_id": group.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create group"}), 500


@app.route("/api/groups/<int:user_id>")
def user_groups(user_id):
    try:
        groups = (
            db.session.query(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .filter(GroupMember.user_id == user_id)
            .all()
        )

        result = []
        for g in groups:
            count = GroupMember.query.filter_by(group_id=g.id).count()
            result.append({"id": g.id, "name": g.name, "member_count": count})

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to fetch groups"}), 500


@app.route("/api/groups/<int:group_id>/members")
def group_members(group_id):
    try:
        members = (
            db.session.query(User)
            .join(GroupMember, User.id == GroupMember.user_id)
            .filter(GroupMember.group_id == group_id)
            .all()
        )

        return jsonify([{"id": u.id, "name": u.name} for u in members])
    except Exception as e:
        return jsonify({"error": "Failed to fetch members"}), 500


# --------------------------------------------------
# EXPENSES
# --------------------------------------------------

@app.route("/api/expenses", methods=["POST"])
def add_expense():
    try:
        data = request.json

        expense = Expense(
            group_id=data["group_id"],
            amount=data["amount"],
            description=data.get("description"),
            paid_by=data["paid_by"]
        )

        db.session.add(expense)
        db.session.commit()

        for uid, amt in data["splits"].items():
            db.session.add(
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=int(uid),
                    amount_owed=amt
                )
            )

        db.session.commit()
        return jsonify({"status": "expense added"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add expense"}), 500


@app.route("/api/expenses/<int:group_id>")
def list_expenses(group_id):
    try:
        expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.created_at.desc()).all()
        result = []

        for e in expenses:
            payer = User.query.get(e.paid_by)
            if payer:
                result.append({
                    "id": e.id,
                    "amount": e.amount,
                    "description": e.description,
                    "payer_name": payer.name,
                    "created_at": e.created_at.isoformat()
                })

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to fetch expenses"}), 500


# --------------------------------------------------
# BALANCES
# --------------------------------------------------

@app.route("/api/balances/<int:group_id>")
def balances(group_id):
    try:
        balances = calculate_balances(group_id)

        if not balance_integrity_ok(balances):
            return jsonify({"error": "Balance integrity violated"}), 500

        result = []
        for uid, bal in balances.items():
            user = User.query.get(uid)
            if user:
                result.append({"user_id": uid, "name": user.name, "balance": round(bal, 2)})

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to calculate balances"}), 500


# --------------------------------------------------
# SETTLEMENTS
# --------------------------------------------------

@app.route("/api/settlements", methods=["POST"])
def add_settlement():
    try:
        data = request.json

        settlement = Settlement(
            group_id=data["group_id"],
            payer_id=data["payer_id"],
            receiver_id=data["receiver_id"],
            amount=data["amount"]
        )

        db.session.add(settlement)
        db.session.commit()
        return jsonify({"status": "settlement recorded"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to record settlement"}), 500


@app.route("/api/settlements/<int:group_id>")
def list_settlements(group_id):
    try:
        settlements = Settlement.query.filter_by(group_id=group_id).order_by(Settlement.created_at.desc()).all()
        result = []

        for s in settlements:
            payer = User.query.get(s.payer_id)
            receiver = User.query.get(s.receiver_id)
            if payer and receiver:
                result.append({
                    "id": s.id,
                    "amount": s.amount,
                    "payer_name": payer.name,
                    "receiver_name": receiver.name,
                    "created_at": s.created_at.isoformat()
                })

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to fetch settlements"}), 500


# --------------------------------------------------
# HTML Routes
# --------------------------------------------------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password", "error")
            return redirect("/login")

        session["user_id"] = user.id
        
        promote_first_user_to_admin()
        
        flash("Logged in successfully", "success")
        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/admin/create-user", methods=["GET", "POST"])
@admin_only
def create_user():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            return render_template(
                "create_user.html",
                error="User already exists"
            )

        try:
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                role="user"
            )

            db.session.add(user)
            db.session.commit()
            
            flash("User created successfully", "success")
            return redirect("/dashboard")
        except Exception as e:
            db.session.rollback()
            return render_template(
                "create_user.html",
                error="Failed to create user"
            )

    return render_template("create_user.html")


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        email = request.form["email"]

        # Check before insert
        if User.query.filter_by(email=email).first():
            return render_template(
                "register.html",
                error="Email already registered"
            )

        user = User(
            name=request.form["name"],
            email=email,
            password=generate_password_hash(request.form["password"])
        )

        try:
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect("/login")
        except Exception as e:
            db.session.rollback()
            return render_template(
                "register.html",
                error="Registration failed"
            )

    return render_template("register.html")


@app.route("/dashboard")
@login_required
def dashboard():

    user_id = session["user_id"]

    groups = (
        db.session.query(Group)
        .outerjoin(GroupMember, Group.id == GroupMember.group_id)
        .filter(
            or_(
                Group.created_by == user_id,
                GroupMember.user_id == user_id
            )
        )
        .distinct()
        .all()
    )

    result = []
    for g in groups:
        count = GroupMember.query.filter_by(group_id=g.id).count()
        result.append({
            "id": g.id,
            "name": g.name,
            "member_count": count
        })

    return render_template("dashboard.html", groups=result)


@app.route("/groups/new", methods=["GET", "POST"])
@login_required
def new_group():

    current_user_id = session["user_id"]

    # GET → show form
    if request.method == "GET":
        users = User.query.filter(User.id != current_user_id).all()
        return render_template("create_group.html", users=users)

    # POST → create group
    group_name = request.form.get("name")
    member_ids = request.form.getlist("members")

    if not group_name:
        users = User.query.filter(User.id != current_user_id).all()
        return render_template(
            "create_group.html",
            users=users,
            error="Group name is required"
        )

    try:
        # Create group
        group = Group(name=group_name, created_by=current_user_id)
        db.session.add(group)
        db.session.commit()

        # Always add creator
        db.session.add(
            GroupMember(group_id=group.id, user_id=current_user_id)
        )

        # Add selected members
        for uid in member_ids:
            db.session.add(
                GroupMember(group_id=group.id, user_id=int(uid))
            )

        db.session.commit()
        flash("Group created successfully", "success")
        return redirect("/dashboard")
    except Exception as e:
        db.session.rollback()
        users = User.query.filter(User.id != current_user_id).all()
        return render_template(
            "create_group.html",
            users=users,
            error="Failed to create group"
        )


@app.route("/groups/<int:group_id>/members", methods=["GET", "POST"])
@login_required
def add_members(group_id):

    current_user_id = session["user_id"]

    # Authorization: only group members can add others
    is_member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user_id
    ).first()

    if not is_member:
        flash("You must be a member of this group", "error")
        return redirect("/dashboard")

    group = Group.query.get_or_404(group_id)

    # Users not already in group
    existing_ids = [
        m.user_id for m in GroupMember.query.filter_by(group_id=group_id).all()
    ]

    available_users = User.query.filter(
        User.id.notin_(existing_ids)
    ).all()

    # GET → show form
    if request.method == "GET":
        return render_template(
            "add_members.html",
            group=group,
            users=available_users
        )

    # POST → add members
    member_ids = request.form.getlist("members")

    if not member_ids:
        return render_template(
            "add_members.html",
            group=group,
            users=available_users,
            error="Select at least one user"
        )

    try:
        for uid in member_ids:
            db.session.add(
                GroupMember(group_id=group_id, user_id=int(uid))
            )

        db.session.commit()
        flash("Members added successfully", "success")
        return redirect(f"/groups/{group_id}")
    except Exception as e:
        db.session.rollback()
        return render_template(
            "add_members.html",
            group=group,
            users=available_users,
            error="Failed to add members"
        )


@app.route("/groups/<int:group_id>")
@login_required
def group_page(group_id):
    

    # Basic authorization
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session["user_id"]
    ).first()

    if not member:
        flash("You don't have access to this group", "error")
        return redirect("/dashboard")

    group = Group.query.get_or_404(group_id)

    balances_raw = calculate_balances(group_id)
    balances = []
    for uid, bal in balances_raw.items():
        user = User.query.get(uid)
        if user:
            balances.append({
                "user_id": uid,  # Added for settlement form
                "name": user.name,
                "balance": round(bal, 2)
            })

    members = (
        db.session.query(User)
        .join(GroupMember, User.id == GroupMember.user_id)
        .filter(GroupMember.group_id == group_id)
        .all()
    )

    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.created_at.desc()).all()

    expense_data = []
    for e in expenses:
        payer = User.query.get(e.paid_by)
        if payer:
            expense_data.append({
                "amount": e.amount,
                "description": e.description,
                "payer_name": payer.name,
                "created_at": e.created_at
            })
        
    suggestions_raw = suggest_settlements(group_id)

    suggestions = []
    for s in suggestions_raw:
        from_user = User.query.get(s["from"])
        to_user = User.query.get(s["to"])
        if from_user and to_user:
            suggestions.append({
                "from_id": s["from"],
                "from_name": from_user.name,
                "to_id": s["to"],
                "to_name": to_user.name,
                "amount": s["amount"]
            })
        
    settlements = (
        Settlement.query
        .filter_by(group_id=group_id)
        .order_by(Settlement.created_at.desc())
        .all()
    )

    settlement_data = []
    for s in settlements:
        payer = User.query.get(s.payer_id)
        receiver = User.query.get(s.receiver_id)
        if payer and receiver:
            settlement_data.append({
                "amount": s.amount,
                "payer_name": payer.name,
                "receiver_name": receiver.name,
                "created_at": s.created_at
            })

    return render_template(
        "group.html",
        group=group,
        balances=balances,
        members=members,
        expenses=expense_data,
        suggestions=suggestions,
        settlements=settlement_data
    )


@app.route("/expenses/add", methods=["POST"])
@login_required
def add_expense_form():

    try:
        group_id = int(request.form["group_id"])
        amount = float(request.form["amount"])
        paid_by = int(request.form["paid_by"])
        description = request.form.get("description", "")

        # Validate amount
        if amount <= 0:
            flash("Amount must be greater than zero", "error")
            return redirect(f"/groups/{group_id}")

        expense = Expense(
            group_id=group_id,
            amount=amount,
            paid_by=paid_by,
            description=description
        )
        db.session.add(expense)
        db.session.commit()

        members = GroupMember.query.filter_by(group_id=group_id).all()
        
        if not members:
            flash("No members in group", "error")
            return redirect(f"/groups/{group_id}")
            
        split_amount = amount / len(members)

        for m in members:
            db.session.add(
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=m.user_id,
                    amount_owed=split_amount
                )
            )

        db.session.commit()
        flash("Expense added successfully", "success")
        return redirect(f"/groups/{group_id}")
    except Exception as e:
        db.session.rollback()
        flash("Failed to add expense", "error")
        return redirect(f"/groups/{group_id}")


@app.route("/settlements/add", methods=["POST"])
@login_required
def add_settlement_form():

    try:
        group_id = int(request.form["group_id"])
        payer_id = int(request.form["payer_id"])
        receiver_id = int(request.form["receiver_id"])
        amount = float(request.form["amount"])

        # Sanity checks
        if payer_id == receiver_id:
            flash("Payer and receiver cannot be the same", "error")
            return redirect(f"/groups/{group_id}")
            
        if amount <= 0:
            flash("Amount must be greater than zero", "error")
            return redirect(f"/groups/{group_id}")

        new_settlement = Settlement(
            group_id=group_id,
            payer_id=payer_id,
            receiver_id=receiver_id,
            amount=amount
        )

        db.session.add(new_settlement)
        db.session.commit()
        
        flash("Settlement recorded successfully", "success")
        return redirect(f"/groups/{group_id}")
    except Exception as e:
        db.session.rollback()
        flash("Failed to record settlement", "error")
        return redirect(f"/groups/{group_id}")

@app.route("/groups/<int:group_id>/delete", methods=["POST"])
@admin_only
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)

    try:
        # delete related data first (important)
        ExpenseSplit.query.filter(
            ExpenseSplit.expense_id.in_(
                db.session.query(Expense.id).filter_by(group_id=group_id)
            )
        ).delete(synchronize_session=False)

        Expense.query.filter_by(group_id=group_id).delete()
        Settlement.query.filter_by(group_id=group_id).delete()
        GroupMember.query.filter_by(group_id=group_id).delete()

        db.session.delete(group)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return "Failed to delete group", 500

    return redirect("/dashboard")





@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect("/login")


# --------------------------------------------------
# RUN
# --------------------------------------------------

with app.app_context():
    db.create_all()
    
if __name__ == "__main__":
    app.run(debug=True)
