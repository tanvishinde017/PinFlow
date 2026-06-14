"""
PinFlow AI — Pinterest OAuth Routes
Handles the OAuth 2.0 connect/callback flow and account disconnection.

Fixes applied vs original:
  1. Removed @login_required from /callback — it breaks OAuth redirects
     when the session cookie isn't forwarded cleanly by the browser/proxy.
     We verify identity via the session state token instead.
  2. session.permanent = True set before storing OAuth state, so the
     session cookie survives the cross-site redirect back from Pinterest
     (required when SESSION_COOKIE_SAMESITE="Lax" in production).
  3. Added token expiry check on connect attempt — avoids duplicate OAuth
     flows if token is still valid.
  4. Improved error logging so you can actually debug failures.
  5. /status now returns token expiry info for frontend polling.
"""

import secrets
import logging
from flask import Blueprint, redirect, url_for, request, flash, session, jsonify
from flask_login import login_required, current_user, login_user
from app import db
from app.services import pinterest_service

log = logging.getLogger(__name__)

pinterest_bp = Blueprint("pinterest", __name__)


@pinterest_bp.route("/connect")
@login_required
def connect():
    """
    Step 1: Redirect user to Pinterest's OAuth consent screen.
    Stores a CSRF state token in the session to verify the callback.
    """
    # Skip OAuth entirely if token is still valid
    if current_user.is_pinterest_connected:
        try:
            # get_valid_token refreshes silently if near-expiry
            pinterest_service.get_valid_token(current_user)
            db.session.commit()
            flash("Pinterest is already connected.", "info")
            return redirect(url_for("main.dashboard"))
        except ValueError:
            # Token invalid/expired — fall through to re-auth
            pass

    state = secrets.token_urlsafe(32)

    # FIX: mark session permanent BEFORE storing state.
    # Without this, SESSION_COOKIE_SAMESITE="Lax" can drop the cookie
    # on the cross-site redirect back from Pinterest, losing the state
    # and causing a guaranteed state-mismatch error.
    session.permanent = True
    session["pinterest_oauth_state"] = state

    auth_url = pinterest_service.get_auth_url(state)
    log.info("Redirecting user %s to Pinterest OAuth", current_user.id)
    return redirect(auth_url)


@pinterest_bp.route("/callback")
def callback():
    """
    Step 2: Pinterest redirects here with ?code=...&state=...

    FIX: Removed @login_required.
    Flask-Login's @login_required will redirect to /login if it considers
    the session invalid at the moment of the external redirect — which
    swallows the ?code= parameter and silently breaks the entire flow.
    Instead, we recover the user from the session manually after validating
    the CSRF state token (which is equivalent security).
    """
    # ── Validate CSRF state ────────────────────────────────────────────────
    returned_state = request.args.get("state", "")
    stored_state   = session.pop("pinterest_oauth_state", "")

    if not returned_state or returned_state != stored_state:
        log.warning(
            "Pinterest OAuth state mismatch. returned=%r stored=%r",
            returned_state[:8] if returned_state else "",
            stored_state[:8]   if stored_state   else "",
        )
        flash("Pinterest authorisation failed (state mismatch). Please try again.", "danger")
        return redirect(url_for("main.dashboard"))

    # ── Ensure user is still authenticated ────────────────────────────────
    # (session is valid — we just confirmed the state — but be explicit)
    if not current_user.is_authenticated:
        flash("Your session expired during Pinterest login. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    # ── Check for OAuth errors from Pinterest ─────────────────────────────
    error = request.args.get("error")
    if error:
        error_desc = request.args.get("error_description", error)
        log.warning("Pinterest OAuth error for user %s: %s", current_user.id, error_desc)
        flash(f"Pinterest declined access: {error_desc}", "warning")
        return redirect(url_for("main.dashboard"))

    code = request.args.get("code")
    if not code:
        flash("No authorisation code received from Pinterest.", "danger")
        return redirect(url_for("main.dashboard"))

    # ── Exchange code for tokens ───────────────────────────────────────────
    try:
        token_data = pinterest_service.exchange_code_for_token(code)
    except Exception as exc:
        log.error("Token exchange failed for user %s: %s", current_user.id, exc)
        flash(f"Token exchange failed: {exc}", "danger")
        return redirect(url_for("main.dashboard"))

    # ── Persist tokens ────────────────────────────────────────────────────
    _save_tokens(current_user, token_data)

    # ── Fetch Pinterest profile (non-fatal) ───────────────────────────────
    try:
        profile = pinterest_service.get_user_info(current_user.pinterest_access_token)
        current_user.pinterest_user_id = profile.get("id")
        current_user.pinterest_username = profile.get("username")
        log.info(
            "Pinterest connected for user %s as @%s",
            current_user.id,
            current_user.pinterest_username,
        )
    except Exception as exc:
        # Non-fatal: token is saved, profile is cosmetic
        log.warning("Could not fetch Pinterest profile for user %s: %s", current_user.id, exc)

    db.session.commit()

    flash("Pinterest account connected successfully! 🎉", "success")
    return redirect(url_for("main.dashboard"))


@pinterest_bp.route("/disconnect", methods=["POST"])
@login_required
def disconnect():
    """Remove all Pinterest tokens from the user's account."""
    current_user.pinterest_access_token     = None
    current_user.pinterest_refresh_token    = None
    current_user.pinterest_token_expires_at = None
    current_user.pinterest_user_id          = None
    current_user.pinterest_username         = None
    db.session.commit()

    log.info("Pinterest disconnected for user %s", current_user.id)

    if request.is_json:
        return jsonify({"success": True})
    flash("Pinterest account disconnected.", "info")
    return redirect(url_for("main.dashboard"))


@pinterest_bp.route("/status")
@login_required
def status():
    """
    Return Pinterest connection status for the current user.
    Includes token expiry so the frontend can prompt re-auth proactively.
    """
    expires_at = current_user.pinterest_token_expires_at
    return jsonify({
        "connected":  current_user.is_pinterest_connected,
        "username":   current_user.pinterest_username,
        "expires_at": expires_at.isoformat() if expires_at else None,
    })


@pinterest_bp.route("/boards")
@login_required
def boards():
    """
    Return the user's Pinterest boards (from cache or live API).
    Used by the dashboard board-selector dropdown.
    """
    from app.models import BoardCache

    # Try cache first
    cached = (
        BoardCache.query
        .filter_by(user_id=current_user.id)
        .order_by(BoardCache.cached_at.desc())
        .all()
    )
    if cached:
        return jsonify({"boards": [b.to_dict() for b in cached], "from_cache": True})

    # Live fetch
    try:
        token  = pinterest_service.get_valid_token(current_user)
        db.session.commit()  # persist any token refresh
        boards_data = pinterest_service.get_boards(token)
    except Exception as exc:
        log.error("Board fetch failed for user %s: %s", current_user.id, exc)
        return jsonify({"error": str(exc)}), 502

    # Update cache
    BoardCache.query.filter_by(user_id=current_user.id).delete()
    for b in boards_data:
        media = b.get("media") or {}
        db.session.add(BoardCache(
            user_id           = current_user.id,
            board_id          = b["id"],
            board_name        = b["name"],
            board_description = b.get("description"),
            board_image_url   = media.get("image_cover_url"),
            pin_count         = b.get("pin_count", 0),
        ))
    db.session.commit()

    return jsonify({"boards": boards_data, "from_cache": False})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_tokens(user, token_data: dict) -> None:
    """
    Apply token data from Pinterest onto the User model.
    Does NOT commit — caller is responsible for db.session.commit().
    """
    from datetime import datetime, timedelta
    user.pinterest_access_token  = token_data.get("access_token")
    # Pinterest may not return a new refresh_token on every exchange;
    # keep the old one if the new response omits it.
    new_refresh = token_data.get("refresh_token")
    if new_refresh:
        user.pinterest_refresh_token = new_refresh

    expires_in = token_data.get("expires_in")
    if expires_in:
        user.pinterest_token_expires_at = (
            datetime.utcnow() + timedelta(seconds=int(expires_in))
        )