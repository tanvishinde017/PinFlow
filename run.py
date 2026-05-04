"""
PinFlow AI — Development Entry Point
Run with: python run.py
"""

import os
from app import create_app, db

app = create_app(os.environ.get("FLASK_ENV", "development"))


@app.cli.command("init-db")
def init_db():
    """Create all database tables (run once after setup)."""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Auto-create tables in development
    app.run(debug=True, host="0.0.0.0", port=5000)
