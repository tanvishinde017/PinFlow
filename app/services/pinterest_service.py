"""
PinFlow AI — Pinterest Service
Handles OAuth 2.0 flow, board fetching, and pin creation via Pinterest API v5.
"""

import requests
from datetime import datetime, timedelta
from flask import current_app
from urllib.parse import urlencode


# Pinterest API v5 base
_API_BASE = "https://api.pinterest.com/v5"
_AUTH_URL = "https://www.pinterest.com/oauth/"
_TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"


# ── OAuth helpers ─────────────────────────────────────────────────────────────

def get_auth_url(state: str) -> str:
    """Build the Pinterest OAuth redirect URL."""
    params = {
        "client_id":     current_app.config["PINTEREST_CLIENT_ID"],
        "redirect_uri":  current_app.config["PINTEREST_REDIRECT_URI"],
        "response_type": "code",
        "scope":         current_app.config["PINTEREST_SCOPE"],
        "state":         state,

    
        "prompt": "select_account",
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    """
    Exchange an authorisation code for access + refresh tokens.
    Returns token dict from Pinterest including access_token, refresh_token, expires_in.
    """
    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": current_app.config["PINTEREST_REDIRECT_URI"],
        },
        auth=(
            current_app.config["PINTEREST_CLIENT_ID"],
            current_app.config["PINTEREST_CLIENT_SECRET"],
        ),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    """Use a refresh token to get a new access token."""
    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=(
            current_app.config["PINTEREST_CLIENT_ID"],
            current_app.config["PINTEREST_CLIENT_SECRET"],
        ),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def ensure_valid_token(user) -> str | None:
    """
    Return a valid access token for a user, refreshing it if necessary.
    Returns None if the user has no Pinterest connection.
    """
    if not user.pinterest_access_token:
        return None

    # If token expires within 5 minutes, refresh it now
    if user.pinterest_token_expires_at:
        buffer = timedelta(minutes=5)
        if datetime.utcnow() + buffer >= user.pinterest_token_expires_at:
            try:
                token_data = refresh_access_token(user.pinterest_refresh_token)
                _apply_token_data(user, token_data)
                from app import db
                db.session.commit()
            except Exception as exc:
                print(f"[pinterest] Token refresh failed for user {user.id}: {exc}")
                return None

    return user.pinterest_access_token


def _apply_token_data(user, token_data: dict) -> None:
    """Write token fields onto a User model instance (does not commit)."""
    user.pinterest_access_token = token_data.get("access_token")
    user.pinterest_refresh_token = token_data.get("refresh_token", user.pinterest_refresh_token)
    expires_in = token_data.get("expires_in")
    if expires_in:
        user.pinterest_token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))


# ── Pinterest API calls ───────────────────────────────────────────────────────

def get_user_info(access_token: str) -> dict:
    """Fetch the authenticated Pinterest user's profile."""
    resp = requests.get(
        f"{_API_BASE}/user_account",
        headers=_auth_headers(access_token),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_boards(access_token: str) -> list[dict]:
    """
    Fetch all boards for the authenticated user (handles pagination).
    Returns list of dicts: {id, name, description, pin_count}.
    """
    boards = []
    url = f"{_API_BASE}/boards"
    params = {"page_size": 100}

    while url:
        resp = requests.get(
            url,
            headers=_auth_headers(access_token),
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        boards.extend(items)
        bookmark = data.get("bookmark")
        params = {"bookmark": bookmark, "page_size": 100} if bookmark else None
        url = url if bookmark else None

    return [
        {
            "id":          b.get("id", ""),
            "name":        b.get("name", ""),
            "description": b.get("description", ""),
            "pin_count":   b.get("pin_count", 0),
            "image_url":   (b.get("media", {}) or {}).get("image_cover_url"),
        }
        for b in boards
    ]


def post_pin(
    access_token: str,
    board_id: str,
    title: str,
    description: str,
    image_url: str,
    link: str,
) -> dict:
    """
    Create a new Pin on Pinterest.

    Args:
        access_token: Valid Pinterest OAuth access token
        board_id:     Pinterest board ID string
        title:        Pin title (max 100 chars)
        description:  Pin description
        image_url:    Publicly accessible image URL
        link:         Destination URL (affiliate link)

    Returns:
        Pinterest API response dict including the new pin's id.
    """
    payload = {
        "board_id": board_id,
        "title":    title[:100],
        "description": description,
        "link":     link,
        "media_source": {
            "source_type": "image_url",
            "url":         image_url,
        },
    }

    resp = requests.post(
        f"{_API_BASE}/pins",
        headers=_auth_headers(access_token),
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def _auth_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }
