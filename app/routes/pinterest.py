"""
PinFlow AI — Pinterest OAuth Routes
Handles the OAuth 2.0 connect/callback flow and account disconnection.
"""

import secrets
from flask import Blueprint, redirect, url_for, request, flash, session, jsonify
from flask_login import login_required, current_user
from app import db
from app.services import pinterest_service

pinterest_bp = Blueprint("pinterest", __name__)


@pinterest_bp.route("/connect")
@login_required
def connect():
    """
    Step 1: Redirect user to Pinterest's OAuth consent screen.
    Stores a CSRF state token in the session to verify the callback.
    """
    state = secrets.token_urlsafe(32)
    session["pinterest_oauth_state"] = state

    auth_url = pinterest_service.get_auth_url(state)
    return redirect(auth_url)


@pinterest_bp.route("/callback")
@login_required
def callback():
    """
    Step 2: Pinterest redirects here with ?code=...&state=...
    Exchange the code for tokens, fetch user info, persist to DB.
    """
    # Validate CSRF state
    returned_state = request.args.get("state", "")
    stored_state   = session.pop("pinterest_oauth_state", "")

    if not returned_state or returned_state != stored_state:
        flash("Pinterest authorisation failed (state mismatch). Please try again.", "danger")
        return redirect(url_for("main.dashboard"))

    code  = request.args.get("code")
    error = request.args.get("error")

    if error:
        flash(f"Pinterest declined access: {error}", "warning")
        return redirect(url_for("main.dashboard"))

    if not code:
        flash("No authorisation code received from Pinterest.", "danger")
        return redirect(url_for("main.dashboard"))

    try:
        token_data = pinterest_service.exchange_code_for_token(code)
    except Exception as exc:
        flash(f"Token exchange failed: {exc}", "danger")
        return redirect(url_for("main.dashboard"))

    # Persist tokens to user record
    _save_tokens(current_user, token_data)

    # Fetch Pinterest profile info
    try:
        profile = pinterest_service.get_user_info(current_user.pinterest_access_token)
        current_user.pinterest_user_id = profile.get("id")
        current_user.pinterest_username = profile.get("username")
    except Exception:
        pass  # Non-fatal — we already have the token

    db.session.commit()

    flash("Pinterest account connected successfully! 🎉", "success")
    return redirect(url_for("main.dashboard"))


@pinterest_bp.route("/disconnect", methods=["POST"])
@login_required
def disconnect():
    """Remove all Pinterest tokens from the user's account."""
    current_user.pinterest_access_token = None
    current_user.pinterest_refresh_token = None
    current_user.pinterest_token_expires_at = None
    current_user.pinterest_user_id = None
    current_user.pinterest_username = None
    db.session.commit()

    if request.is_json:
        return jsonify({"success": True})
    flash("Pinterest account disconnected.", "info")
    return redirect(url_for("main.dashboard"))


@pinterest_bp.route("/status")
@login_required
def status():
    """Return Pinterest connection status for the current user."""
    return jsonify({
        "connected": current_user.is_pinterest_connected,
        "username":  current_user.pinterest_username,
    })


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_tokens(user, token_data: dict) -> None:
    """Apply token data from Pinterest onto the User model (does not commit)."""
    from datetime import datetime, timedelta
    user.pinterest_access_token  = token_data.get("access_token")
    user.pinterest_refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    if expires_in:
        user.pinterest_token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
