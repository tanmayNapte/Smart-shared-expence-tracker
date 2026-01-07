from flask import Flask, request, jsonify, session, render_template, redirect, url_for,flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import os
from sqlalchemy import or_

# --------------------------------------------------
# APP SETUP
# --------------------------------------------------

# Update this section in app.py
load_dotenv()

app = Flask(__name__)

# Logic to fix the database URI for production
uri = os.getenv("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

db = SQLAlchemy(app)

# --------------------------------------------------
# MODELS
# --------------------------------------------------

class User(db.Model):
    __tablename__ = "expense_users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default="user")  # admin / user


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExpenseSplit(db.Model):
    __tablename__ = "expense_splits"

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("expense_users.id"))
    amount_owed = db.Column(db.Float, nullable=False)


class Settlement(db.Model):
    __tablename__ = "settlements"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"))
    payer_id = db.Column(db.Integer, db.ForeignKey("expense_users.id"))
    receiver_id = db.Column(db.Integer, db.ForeignKey("expense_users.id"))
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --------------------------------------------------
# INIT (DEV ONLY)
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

from sqlalchemy import select

def promote_first_user_to_admin():
    # Check if an admin already exists
    admin_exists = db.session.execute(
        select(User).where(User.role == "admin")
    ).first()

    if admin_exists:
        return  # Do nothing if admin already exists

    # Get the first user (lowest id)
    first_user = db.session.execute(
        select(User).order_by(User.id)
    ).scalar_one_or_none()

    if first_user:
        first_user.role = "admin"
        db.session.commit()


# --------------------------------------------------
# AUTH
# --------------------------------------------------

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    hashed = generate_password_hash(data["password"])

    user = User(
        name=data["name"],
        email=data["email"],
        password=hashed
    )

    db.session.add(user)
    db.session.commit()
    return jsonify({"id": user.id, "name": user.name, "email": user.email})


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()

    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"id": user.id, "name": user.name, "email": user.email})

# --------------------------------------------------
# USERS
# --------------------------------------------------

@app.route("/api/users")
def all_users():
    users = User.query.all()
    return jsonify([{"id": u.id, "name": u.name, "email": u.email} for u in users])

# --------------------------------------------------
# GROUPS
# --------------------------------------------------

@app.route("/api/groups", methods=["POST"])
def create_group():
    data = request.json
    group = Group(name=data["name"], created_by=data["creator_id"])
    db.session.add(group)
    db.session.commit()

    for uid in data["member_ids"]:
        db.session.add(GroupMember(group_id=group.id, user_id=uid))

    db.session.commit()
    return jsonify({"group_id": group.id})


@app.route("/api/groups/<int:user_id>")
def user_groups(user_id):
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


@app.route("/api/groups/<int:group_id>/members")
def group_members(group_id):
    members = (
        db.session.query(User)
        .join(GroupMember, User.id == GroupMember.user_id)
        .filter(GroupMember.group_id == group_id)

        .all()
    )

    return jsonify([{"id": u.id, "name": u.name} for u in members])

# --------------------------------------------------
# EXPENSES
# --------------------------------------------------

@app.route("/api/expenses", methods=["POST"])
def add_expense():
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


@app.route("/api/expenses/<int:group_id>")
def list_expenses(group_id):
    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.created_at.desc()).all()
    result = []

    for e in expenses:
        payer = User.query.get(e.paid_by)
        result.append({
            "id": e.id,
            "amount": e.amount,
            "description": e.description,
            "payer_name": payer.name,
            "created_at": e.created_at.isoformat()
        })

    return jsonify(result)

# --------------------------------------------------
# BALANCES
# --------------------------------------------------

@app.route("/api/balances/<int:group_id>")
def balances(group_id):
    balances = calculate_balances(group_id)

    if not balance_integrity_ok(balances):
        return jsonify({"error": "Balance integrity violated"}), 500

    result = []
    for uid, bal in balances.items():
        user = User.query.get(uid)
        result.append({"user_id": uid, "name": user.name, "balance": round(bal, 2)})

    return jsonify(result)

# --------------------------------------------------
# SETTLEMENTS
# --------------------------------------------------

@app.route("/api/settlements", methods=["POST"])
def add_settlement():
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


@app.route("/api/settlements/<int:group_id>")
def list_settlements(group_id):
    settlements = Settlement.query.filter_by(group_id=group_id).order_by(Settlement.created_at.desc()).all()
    result = []

    for s in settlements:
        payer = User.query.get(s.payer_id)
        receiver = User.query.get(s.receiver_id)
        result.append({
            "id": s.id,
            "amount": s.amount,
            "payer_name": payer.name,
            "receiver_name": receiver.name,
            "created_at": s.created_at.isoformat()
        })

    return jsonify(result)

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
def create_user():
    if not admin_required():
        return redirect("/dashboard")

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            return render_template(
                "create_user.html",
                error="User already exists"
            )

        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role="user"
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/dashboard")

    return render_template("create_user.html")


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        user = User(
            name=request.form["name"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

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
def new_group():
    if "user_id" not in session:
        return redirect("/login")

    current_user_id = session["user_id"]

    # GET → show form
    if request.method == "GET":
        users = User.query.filter(User.id != current_user_id).all()
        return render_template("create_group.html", users=users)

    # POST → create group
    group_name = request.form.get("name")
    member_ids = request.form.getlist("members")  # optional

    if not group_name:
        users = User.query.filter(User.id != current_user_id).all()
        return render_template(
            "create_group.html",
            users=users,
            error="Group name is required"
        )

    # Create group
    group = Group(name=group_name, created_by=current_user_id)
    db.session.add(group)
    db.session.commit()

    # Always add creator
    db.session.add(
        GroupMember(group_id=group.id, user_id=current_user_id)
    )

    # Add selected members (if any)
    for uid in member_ids:
        db.session.add(
            GroupMember(group_id=group.id, user_id=int(uid))
        )

    db.session.commit()
    return redirect("/dashboard")


@app.route("/groups/<int:group_id>/members", methods=["GET", "POST"])
def add_members(group_id):
    if "user_id" not in session:
        return redirect("/login")

    current_user_id = session["user_id"]

    # Authorization: only group members can add others
    is_member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user_id
    ).first()

    if not is_member:
        return "Unauthorized", 403

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

    for uid in member_ids:
        db.session.add(
            GroupMember(group_id=group_id, user_id=int(uid))
        )

    db.session.commit()
    return redirect(f"/groups/{group_id}")



@app.route("/groups/<int:group_id>")
def group_page(group_id):
    if "user_id" not in session:
        return redirect("/login")

    # Basic authorization
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session["user_id"]
    ).first()

    if not member:
        return "Unauthorized", 403

    group = Group.query.get_or_404(group_id)

    balances_raw = calculate_balances(group_id)
    balances = []
    for uid, bal in balances_raw.items():
        user = User.query.get(uid)
        balances.append({
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
        expense_data.append({
            "amount": e.amount,
            "description": e.description,
            "payer_name": payer.name
        })
        
    suggestions_raw = suggest_settlements(group_id)

    suggestions = []
    for s in suggestions_raw:
        suggestions.append({
            "from_name": User.query.get(s["from"]).name,
            "to_name": User.query.get(s["to"]).name,
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
def add_expense_form():
    if "user_id" not in session:
        return redirect("/login")

    group_id = int(request.form["group_id"])
    amount = float(request.form["amount"])
    paid_by = int(request.form["paid_by"])
    description = request.form.get("description")

    expense = Expense(
        group_id=group_id,
        amount=amount,
        paid_by=paid_by,
        description=description
    )
    db.session.add(expense)
    db.session.commit()

    members = GroupMember.query.filter_by(group_id=group_id).all()
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
    return redirect(f"/groups/{group_id}")

def suggest_settlements(group_id):
    balances = calculate_balances(group_id)

    creditors = []
    debtors = []

    for user_id, balance in balances.items():
        if balance > 0:
            creditors.append([user_id, balance])
        elif balance < 0:
            debtors.append([user_id, -balance])  # store positive owed amount

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

        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1

    return suggestions

@app.route("/settlements/add", methods=["POST"])
def add_settlement_form():
    if "user_id" not in session:
        return redirect("/login")

    group_id = int(request.form["group_id"])
    payer_id = int(request.form["payer_id"])
    receiver_id = int(request.form["receiver_id"])
    amount = float(request.form["amount"])

    # Sanity checks
    if payer_id == receiver_id or amount <= 0:
        return redirect(f"/groups/{group_id}")

    new_settlement = Settlement(
        group_id=group_id,
        payer_id=payer_id,
        receiver_id=receiver_id,
        amount=amount
    )

    db.session.add(new_settlement)
    db.session.commit()

    return redirect(f"/groups/{group_id}")



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")



# --------------------------------------------------
# RUN
# --------------------------------------------------

with app.app_context():
    db.create_all()
    
if __name__ == "__main__":
    # Get port from environment or default to 5000 for local dev
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)