import os
from datetime import timedelta
from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    # ── Core ──────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = False
    TESTING = False

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://localhost/pinflow"
    )
    # Heroku/Railway returns postgres:// but SQLAlchemy needs postgresql://
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TIMEZONE = "UTC"
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_MAX_RETRIES = 3

    # ── Session ───────────────────────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = REDIS_URL

    # ── Third-party APIs ──────────────────────────────────────────────────────
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

    PINTEREST_CLIENT_ID = os.environ.get("PINTEREST_CLIENT_ID", "")
    PINTEREST_CLIENT_SECRET = os.environ.get("PINTEREST_CLIENT_SECRET", "")
    PINTEREST_REDIRECT_URI = os.environ.get(
        "PINTEREST_REDIRECT_URI", "http://localhost:5000/pinterest/callback"
    )
    PINTEREST_SCOPE = "boards:read,pins:write,user_accounts:read"

    # ── Image Storage ─────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "app", "static", "downloads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://localhost/pinflow_dev"
    )


class ProductionConfig(Config):
    DEBUG = False
    # Force secure session cookie in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
