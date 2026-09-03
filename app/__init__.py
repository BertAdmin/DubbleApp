import os
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from app.config import Config
from app.models import db, User
from app.auth import LoginUser

login_manager = LoginManager()
csrf = CSRFProtect()
server_session = Session()


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    )
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    server_session.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(User, int(user_id))
        if user is None:
            return None
        return LoginUser(user)

    from app.routes.auth_routes import auth_bp
    from app.routes.bubble_routes import bubble_bp
    from app.routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(bubble_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
