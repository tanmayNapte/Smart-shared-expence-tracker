from models import db, User
from config import Config
from flask_migrate import Migrate
from routes.auth import auth_bp
from routes.users import users_bp
from routes.groups import groups_bp
from routes.expenses import expenses_bp
from routes.settlements import settlements_bp
from routes.debug import debug_bp

from services.admin_panel import setup_admin
from flask import Flask, session

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

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
app.register_blueprint(debug_bp)

# with app.app_context():
#    db.create_all()
setup_admin(app)
if __name__ == "__main__":
    app.run(port=8001, debug=True)

