"""
PinFlow AI — Celery Worker Entry Point

Run with:
  celery -A celery_worker.celery worker --loglevel=info
"""

import os
from app import create_app, celery

# Create Flask app and configure Celery within its context to ensure it has access to the app's configuration
app = create_app(os.environ.get("FLASK_ENV", "development"))

# Import tasks so Celery discovers them when the worker starts. This should be done after creating the app to ensure tasks have access to the app context.  
import app.tasks  # noqa: F401, E402


# This allows `celery -A celery_worker.celery worker` to work without needing to set the FLASK_APP environment variable
__all__ = ["celery"]
