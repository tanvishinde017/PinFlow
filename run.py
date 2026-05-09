"""
PinFlow AI — Development Entry Point
Run with: python run.py to start the Flask development server on http://localhost:5000.
Includes a CLI command 'init-db' to create database tables after setup.
"""

import os
from app import create_app, db

app = create_app(os.environ.get("FLASK_ENV", "development"))


@app.cli.command("init-db")
def init_db():
    """Create all database tables (run once after setup)."""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created.") #db.create_all() is also called in the main block for convenience in development mode.


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Auto-create tables in development mode (ensure this is only used in development, not in production)
    app.run(debug=True, host="0.0.0.0", port=5000)
