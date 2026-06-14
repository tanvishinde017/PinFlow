"""
PinFlow AI — Configuration
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(**file**))

class Config:
# ------------------------------------------------------------------
# Core Settings
# ------------------------------------------------------------------
SECRET_KEY = os.environ.get(
"SECRET_KEY",
"dev-secret-change-in-production"
)

```
DEBUG = False
TESTING = False

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://localhost/pinflow"
)

# Fix for Heroku/Railway
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

SQLALCHEMY_DATABASE_URI = DATABASE_URL
SQLALCHEMY_TRACK_MODIFICATIONS = False

SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# ------------------------------------------------------------------
# Session Settings
# ------------------------------------------------------------------
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# ------------------------------------------------------------------
# File Uploads
# ------------------------------------------------------------------
UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "app",
    "static",
    "downloads"
)

MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

# ------------------------------------------------------------------
# Redis / Celery
# ------------------------------------------------------------------
REDIS_URL = os.environ.get(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_MAX_RETRIES = 3

# ------------------------------------------------------------------
# Rate Limiting
# ------------------------------------------------------------------
RATELIMIT_DEFAULT = "200 per day;50 per hour"
RATELIMIT_STORAGE_URL = REDIS_URL

# ------------------------------------------------------------------
# AI API
# ------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get(
    "ANTHROPIC_API_KEY",
    ""
)

# ------------------------------------------------------------------
# Pinterest API
# ------------------------------------------------------------------
PINTEREST_CLIENT_ID = os.environ.get(
    "PINTEREST_CLIENT_ID",
    ""
)

PINTEREST_CLIENT_SECRET = os.environ.get(
    "PINTEREST_CLIENT_SECRET",
    ""
)

PINTEREST_REDIRECT_URI = os.environ.get(
    "PINTEREST_REDIRECT_URI",
    "http://localhost:5000/pinterest/callback"
)

PINTEREST_SCOPE = (
    "boards:read,"
    "pins:read,"
    "pins:write,"
    "user_accounts:read"
)

PINTEREST_ACCESS_TOKEN = os.environ.get(
    "PINTEREST_ACCESS_TOKEN",
    ""
)

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
LOG_LEVEL = os.environ.get(
    "LOG_LEVEL",
    "INFO"
)
```

class DevelopmentConfig(Config):
DEBUG = True

```
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    "postgresql://localhost/pinflow_dev"
)
```

class ProductionConfig(Config):
DEBUG = False

```
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
```

class TestingConfig(Config):
TESTING = True

```
SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
WTF_CSRF_ENABLED = False
```

config = {
"development": DevelopmentConfig,
"production": ProductionConfig,
"testing": TestingConfig,
"default": DevelopmentConfig,
}
