"""
PinFlow AI — Development Entry Point

Run:
    python run.py

Starts the Flask development server on:
    http://localhost:5000

CLI Commands:
    flask init-db
        Creates database tables manually .
"""

import os
from app import create_app, db

# Get environment (default = development)
ENV = os.environ.get("FLASK_ENV", "development")

# Create Flask application
app = create_app(ENV)


@app.cli.command("init-db")
def init_db():
    """
    Create all database tables.

    Usage:
        flask init-db
    """
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully.")


def initialize_database():
    """
    Automatically create tables in development mode only.
    """
    if ENV == "development":
        with app.app_context():
            db.create_all()
            print("✅ Database initialized (development mode).")


if __name__ == "__main__":
    # Auto-create tables only in development
    initialize_database()

    print(f"🚀 Starting PinFlow AI in {ENV} mode...")
    print("🌐 Server running at: http://localhost:5000")

    app.run(
        debug=(ENV == "development"),
        host="0.0.0.0",
        port=5000
    )
