"""
PinFlow AI — Pinterest Service
Handles all Pinterest API v5 interactions:
  - OAuth URL generation
  - Authorization code → token exchange
  - Token refresh
  - User profile fetch
  - Board listing
  - Pin creation
"""

import base64
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
from flask import current_app


# ── Constants ─────────────────────────────────────────────────────────────────

PINTEREST_AUTH_URL   = "https://www.pinterest.com/oauth/"
PINTEREST_TOKEN_URL  = "https://api.pinterest.com/v5/oauth/token"
PINTEREST_API_BASE   = "https://api.pinterest.com/v5"


# ── OAuth helpers ─────────────────────────────────────────────────────────────

def get_auth_url(state: str) -> str:
    """
    Build the Pinterest OAuth consent-screen URL.
    Uses v5 OAuth endpoint — the old /oauth/authorize endpoint is deprecated.
    """
    params = {
        "client_id":     current_app.config["PINTEREST_CLIENT_ID"],
        "redirect_uri":  current_app.config["PINTEREST_REDIRECT_URI"],
        "response_type": "code",
        "scope":         current_app.config["PINTEREST_SCOPE"],
        "state":         state,
    }
    return f"{PINTEREST_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    """
    Exchange an authorization code for access + refresh tokens.

    Pinterest v5 requires HTTP Basic Auth using client_id:client_secret,
    NOT passing them as body params (a common mistake with older guides).

    Returns dict with: access_token, refresh_token, expires_in, token_type, scope
    Raises: requests.HTTPError on failure (caller should catch)
    """
    client_id     = current_app.config["PINTEREST_CLIENT_ID"]
    client_secret = current_app.config["PINTEREST_CLIENT_SECRET"]
    redirect_uri  = current_app.config["PINTEREST_REDIRECT_URI"]

    # Pinterest v5 requires Basic Auth — credentials in Authorization header
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type":  "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type":   "authorization_code",
        "code":         code,
        "redirect_uri": redirect_uri,
    }

    resp = requests.post(PINTEREST_TOKEN_URL, headers=headers, data=payload, timeout=15)

    # Raise with the actual Pinterest error body so the caller can log it
    if not resp.ok:
        raise requests.HTTPError(
            f"Pinterest token exchange failed [{resp.status_code}]: {resp.text}",
            response=resp,
        )

    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    """
    Use a refresh token to get a new access token.
    Call this when `user.pinterest_token_expires_at` is in the past.

    Returns the same shape as exchange_code_for_token.
    """
    client_id     = current_app.config["PINTEREST_CLIENT_ID"]
    client_secret = current_app.config["PINTEREST_CLIENT_SECRET"]

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type":  "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
    }

    resp = requests.post(PINTEREST_TOKEN_URL, headers=headers, data=payload, timeout=15)

    if not resp.ok:
        raise requests.HTTPError(
            f"Pinterest token refresh failed [{resp.status_code}]: {resp.text}",
            response=resp,
        )

    return resp.json()


# ── API helpers ───────────────────────────────────────────────────────────────

def _get(endpoint: str, access_token: str, params: dict = None) -> dict:
    """Authenticated GET against the Pinterest v5 API."""
    url  = f"{PINTEREST_API_BASE}{endpoint}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params or {},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _post(endpoint: str, access_token: str, payload: dict) -> dict:
    """Authenticated POST against the Pinterest v5 API."""
    url  = f"{PINTEREST_API_BASE}{endpoint}"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        },
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Business logic ────────────────────────────────────────────────────────────

def get_user_info(access_token: str) -> dict:
    """
    Fetch the connected Pinterest user's profile.
    Returns dict with at least: username, id, profile_image
    """
    return _get("/user_account", access_token)


def get_boards(access_token: str, page_size: int = 50) -> list[dict]:
    """
    Return a list of the user's Pinterest boards.
    Handles pagination automatically up to `page_size` boards.

    Each board dict has: id, name, description, media (cover image), pin_count
    """
    data   = _get("/boards", access_token, params={"page_size": page_size})
    return data.get("items", [])


def create_pin(
    access_token: str,
    board_id: str,
    title: str,
    description: str,
    image_url: str,
    link: str = None,
    alt_text: str = None,
) -> dict:
    """
    Create a pin on the specified board via the v5 API.

    Pinterest v5 requires media.source.url — NOT image_url at the top level
    (a very common source of 400 errors from people following old tutorials).

    Returns the created pin object including its id.
    """
    payload: dict = {
        "board_id": board_id,
        "title":    title,
        "description": description,
        "media_source": {
            "source_type": "image_url",
            "url":         image_url,
        },
    }
    if link:
        payload["link"] = link
    if alt_text:
        payload["alt_text"] = alt_text

    return _post("/pins", access_token, payload)


# ── Token management utility ──────────────────────────────────────────────────

def get_valid_token(user) -> str:
    """
    Return a valid access token for `user`, refreshing it first if expired.
    Updates `user` in-place but does NOT commit — caller must db.session.commit().

    Raises ValueError if the user has no tokens at all.
    """
    if not user.pinterest_access_token:
        raise ValueError("User has no Pinterest access token.")

    # Check expiry — refresh if within 5 minutes of expiry
    if user.pinterest_token_expires_at:
        buffer = timedelta(minutes=5)
        if datetime.utcnow() >= (user.pinterest_token_expires_at - buffer):
            if not user.pinterest_refresh_token:
                raise ValueError("Access token expired and no refresh token available.")

            token_data = refresh_access_token(user.pinterest_refresh_token)
            _apply_tokens(user, token_data)

    return user.pinterest_access_token


def _apply_tokens(user, token_data: dict) -> None:
    """Write token fields onto user object. Does NOT commit."""
    user.pinterest_access_token  = token_data.get("access_token")
    user.pinterest_refresh_token = token_data.get("refresh_token", user.pinterest_refresh_token)
    expires_in = token_data.get("expires_in")
    if expires_in:
        user.pinterest_token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))