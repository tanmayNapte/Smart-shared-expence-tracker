from flask import Flask, session
from models import db, User
from config import Config

from routes.auth import auth_bp
from routes.users import users_bp
from routes.groups import groups_bp
from routes.expenses import expenses_bp
from routes.settlements import settlements_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

@app.context_processor
def inject_current_user():
    if "user_id" in session:
        return {"current_user": db.session.get(User, session["user_id"])}
    return {"current_user": None}

app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(groups_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(settlements_bp)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
