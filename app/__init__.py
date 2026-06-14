"""
PinFlow AI — Application Factory
Wires together Flask extensions and registers all blueprints.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from celery import Celery

from config import config

# ── Extension singletons (bound to app later via init_app) ───────────────────
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)

# Global Celery instance — configured inside create_app
celery = Celery(__name__)


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    # Ensure the download folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Initialise extensions ─────────────────────────────────────────────────
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access PinFlow AI."
    login_manager.login_message_category = "info"

    # ── Configure Celery ──────────────────────────────────────────────────────
    _configure_celery(app)

    # ── Register blueprints ───────────────────────────────────────────────────
    from app.routes.auth import auth_bp
    from app.routes.api import api_bp
    from app.routes.pinterest import pinterest_bp
    from app.routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(pinterest_bp, url_prefix="/pinterest")
    app.register_blueprint(main_bp)

    # ── User loader for Flask-Login ───────────────────────────────────────────
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # ── Shell context ─────────────────────────────────────────────────────────
    @app.shell_context_processor
    def make_shell_context():
        from app.models import User, Pin, BoardCache
        return {"db": db, "User": User, "Pin": Pin, "BoardCache": BoardCache}

    return app


def _configure_celery(app: Flask) -> None:
    """Push Flask app context into Celery tasks."""
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        task_serializer=app.config["CELERY_TASK_SERIALIZER"],
        result_serializer=app.config["CELERY_RESULT_SERIALIZER"],
        accept_content=app.config["CELERY_ACCEPT_CONTENT"],
        timezone=app.config["CELERY_TIMEZONE"],
        task_track_started=app.config["CELERY_TASK_TRACK_STARTED"],
    )

    class ContextTask(celery.Task):
        """Ensures every Celery task runs inside a Flask app context."""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
