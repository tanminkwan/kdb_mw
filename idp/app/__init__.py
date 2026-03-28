import logging
import sys

from flask import Flask
from flask_login import LoginManager
from .models import db
from .config import Config


login_manager = LoginManager()


def create_app(config_class=None):
    """Flask app factory. SOLID: 단일 책임 - 앱 초기화만 담당."""
    app = Flask(__name__)

    if config_class is None:
        config_class = Config
    app.config.from_object(config_class)

    # Logging
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    # DB & Login
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        from .models import IdpUser
        # return IdpUser.query.get(int(user_id))
        return db.session.get(IdpUser, int(user_id))

    with app.app_context():
        db.create_all()
        _register_default_client(app)

    # Blueprints
    from .routes import auth_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app


def _register_default_client(app):
    """초기 OAuth2 Client(mwm-app) 자동 등록"""
    from .models import OAuth2Client

    client_id = app.config["DEFAULT_CLIENT_ID"]
    existing = OAuth2Client.query.filter_by(client_id=client_id).first()
    if not existing:
        client = OAuth2Client(
            client_id=client_id,
            client_secret=app.config["DEFAULT_CLIENT_SECRET"],
            client_name="MWM App",
            redirect_uris=app.config["DEFAULT_REDIRECT_URI"],
            grant_types="authorization_code refresh_token",
            scope="openid profile email",
        )
        db.session.add(client)
        db.session.commit()
        logging.info(f"Default OAuth2 client '{client_id}' registered.")
