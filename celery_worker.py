"""
PinFlow AI — Celery Worker Entry Point

Run with:
  celery -A celery_worker.celery worker --loglevel=info
"""

import os
from app import create_app, celery

# Create Flask app and configure Celery within its context
app = create_app(os.environ.get("FLASK_ENV", "development"))

# Import tasks so Celery discovers them
import app.tasks  # noqa: F401, E402


# This allows `celery -A celery_worker.celery worker` to work
__all__ = ["celery"]
