"""
PinFlow AI — Authentication Routes
Handles signup, login, and logout with Flask-Login and Flask-Bcrypt.
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Render signup form (GET) or create a new user account (POST)."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        # ── Validation ────────────────────────────────────────────────────────
        if not email or not password:
            msg = "Email and password are required."
            return _respond(request, 400, error=msg)

        if len(password) < 8:
            msg = "Password must be at least 8 characters."
            return _respond(request, 400, error=msg)

        if User.query.filter_by(email=email).first():
            msg = "An account with that email already exists."
            return _respond(request, 409, error=msg)

        # ── Create user ───────────────────────────────────────────────────────
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(email=email, password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()

        login_user(user, remember=True)

        if request.is_json:
            return jsonify({"success": True, "redirect": url_for("main.dashboard")})
        flash("Welcome to PinFlow AI! 🎉", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Render login form (GET) or authenticate user (POST)."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            msg = "Invalid email or password."
            return _respond(request, 401, error=msg)

        login_user(user, remember=True)

        if request.is_json:
            return jsonify({"success": True, "redirect": url_for("main.dashboard")})
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("auth.login"))


# ── Helper ────────────────────────────────────────────────────────────────────

def _respond(req, status: int, error: str):
    """Return JSON or redirect based on whether request is AJAX."""
    if req.is_json:
        return jsonify({"error": error}), status
    flash(error, "danger")
    return redirect(req.url)
