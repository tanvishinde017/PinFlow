"""
PinFlow AI — Pinterest Service
Supports BOTH:
1. Sandbox Access Token (current)
2. OAuth Flow (future when approved)
"""

import requests
from datetime import datetime, timedelta
from flask import current_app
from urllib.parse import urlencode


_API_BASE = "https://api.pinterest.com/v5"
_AUTH_URL = "https://www.pinterest.com/oauth/"
_TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"


# ─────────────────────────────────────────────────────────────
# 🔐 AUTH URL (OAuth - future use)
# ─────────────────────────────────────────────────────────────

def get_auth_url(state: str) -> str:
    params = {
        "client_id": current_app.config["PINTEREST_CLIENT_ID"],
        "redirect_uri": current_app.config["PINTEREST_REDIRECT_URI"],
        "response_type": "code",
        "scope": current_app.config["PINTEREST_SCOPE"],
        "state": state,
        "prompt": "select_account",
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


# ─────────────────────────────────────────────────────────────
# 🔄 TOKEN MANAGEMENT
# ─────────────────────────────────────────────────────────────

def exchange_code_for_token(code: str) -> dict:
    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
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
    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "refresh_token",
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


# ─────────────────────────────────────────────────────────────
# 🔑 TOKEN HANDLER (SMART SWITCH)
# ─────────────────────────────────────────────────────────────

def ensure_valid_token(user=None) -> str | None:
    """
    Returns a valid access token.

    Priority:
    1. Sandbox token (for development)
    2. User OAuth token (future)
    """

    # ✅ SANDBOX MODE (CURRENT)
    sandbox_token = current_app.config.get("PINTEREST_ACCESS_TOKEN")
    if sandbox_token:
        return sandbox_token

    # ❌ If no user or no OAuth token
    if not user or not user.pinterest_access_token:
        return None

    # 🔄 Refresh if expiring
    if user.pinterest_token_expires_at:
        buffer = timedelta(minutes=5)
        if datetime.utcnow() + buffer >= user.pinterest_token_expires_at:
            try:
                token_data = refresh_access_token(user.pinterest_refresh_token)
                _apply_token_data(user, token_data)

                from app import db
                db.session.commit()

            except Exception as exc:
                print(f"[pinterest] Token refresh failed: {exc}")
                return None

    return user.pinterest_access_token


def _apply_token_data(user, token_data: dict):
    user.pinterest_access_token = token_data.get("access_token")
    user.pinterest_refresh_token = token_data.get(
        "refresh_token", user.pinterest_refresh_token
    )

    expires_in = token_data.get("expires_in")
    if expires_in:
        user.pinterest_token_expires_at = datetime.utcnow() + timedelta(
            seconds=int(expires_in)
        )


# ─────────────────────────────────────────────────────────────
# 📌 API CALLS
# ─────────────────────────────────────────────────────────────

def get_user_info(access_token: str) -> dict:
    resp = requests.get(
        f"{_API_BASE}/user_account",
        headers=_auth_headers(access_token),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_boards(access_token: str) -> list:
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

        boards.extend(data.get("items", []))

        bookmark = data.get("bookmark")
        if bookmark:
            params = {"bookmark": bookmark, "page_size": 100}
        else:
            break

    return [
        {
            "id": b.get("id"),
            "name": b.get("name"),
            "pin_count": b.get("pin_count", 0),
            "image_url": (b.get("media") or {}).get("image_cover_url"),
        }
        for b in boards
    ]


def post_pin(access_token, board_id, title, description, image_url, link):
    payload = {
        "board_id": board_id,
        "title": title[:100],
        "description": description,
        "link": link,
        "media_source": {
            "source_type": "image_url",
            "url": image_url,
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


def _auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }