"""
PinFlow AI — Core API Routes
POST /api/fetch       → scrape Amazon product
POST /api/generate    → generate AI Pinterest content
POST /api/post-pin    → queue pin for posting
GET  /api/boards      → list user's Pinterest boards
GET  /api/history     → last 50 pins for current user
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db, limiter
from app.models import Pin, BoardCache
from app.services import scraper, ai_service, pinterest_service, image_service
from app.tasks import post_pin_to_pinterest

api_bp = Blueprint("api", __name__)


# ── /api/fetch ────────────────────────────────────────────────────────────────

@api_bp.route("/fetch", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def fetch():
    """Scrape an Amazon link and return product data + lifestyle image options."""
    data = request.get_json(silent=True) or {}
    link = (data.get("link") or "").strip()

    if not link:
        return jsonify({"error": "No link provided"}), 400

    product = scraper.get_product_data(link)
    keywords = scraper.extract_keywords(product["title"])
    lifestyle_images = scraper.get_lifestyle_images(keywords)

    return jsonify({
        "title":         product["title"],
        "price":         product["price"],
        "product_image": product["image"],
        "images":        lifestyle_images,
        "link":          link,
    })


# ── /api/generate ─────────────────────────────────────────────────────────────

@api_bp.route("/generate", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def generate():
    """
    Generate 5 titles, 5 descriptions, hashtags and CTA via Claude.
    Accepts: { title, price, tone }
    """
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    price = (data.get("price") or "N/A").strip()
    tone  = (data.get("tone") or "viral").strip()

    if not title:
        return jsonify({"error": "Product title is required"}), 400

    valid_tones = {"viral", "luxury", "casual", "affiliate"}
    if tone not in valid_tones:
        tone = "viral"

    try:
        content = ai_service.generate_pin_content(title, price, tone)
    except Exception as exc:
        print(f"[api/generate] AI error: {exc}")
        content = ai_service._fallback_content(title, tone)

    return jsonify(content)


# ── /api/post-pin ─────────────────────────────────────────────────────────────

@api_bp.route("/post-pin", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def post_pin():
    """
    Save a pin record and enqueue it for posting to Pinterest via Celery.

    Accepts:
    {
        "title":          str,
        "description":    str,
        "hashtags":       str,
        "cta":            str,
        "tone":           str,
        "image_url":      str,
        "affiliate_link": str,
        "board_id":       str,
        "board_name":     str,
        "product_title":  str,
        "product_price":  str,
    }
    """
    data = request.get_json(silent=True) or {}

    required = ["title", "board_id", "image_url"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    if not current_user.is_pinterest_connected:
        return jsonify({"error": "Connect your Pinterest account first"}), 403

    # Optionally download and store the image locally
    image_url = data["image_url"]
    local_path = image_service.download_and_save(image_url)
    if local_path:
        # Build an absolute URL so Pinterest can fetch it
        from flask import request as flask_request
        image_url = flask_request.host_url.rstrip("/") + local_path

    pin = Pin(
        user_id=current_user.id,
        title=data["title"],
        description=data.get("description", ""),
        hashtags=data.get("hashtags", ""),
        cta=data.get("cta", ""),
        tone=data.get("tone", "viral"),
        image_url=image_url,
        affiliate_link=data.get("affiliate_link", ""),
        board_id=data["board_id"],
        board_name=data.get("board_name", ""),
        product_title=data.get("product_title", ""),
        product_price=data.get("product_price", ""),
        status="draft",
    )
    db.session.add(pin)
    db.session.commit()

    # Dispatch async Celery task
    task = post_pin_to_pinterest.delay(pin.id)

    return jsonify({
        "success": True,
        "pin_id":  pin.id,
        "task_id": task.id,
        "message": "Pin queued for posting!",
    })


# ── /api/boards ───────────────────────────────────────────────────────────────

@api_bp.route("/boards", methods=["GET"])
@login_required
@limiter.limit("20 per minute")
def boards():
    """Return cached boards or fetch fresh ones from Pinterest."""
    if not current_user.is_pinterest_connected:
        return jsonify({"error": "Connect Pinterest first", "boards": []}), 403

    # Try DB cache first (valid for 1 hour)
    cached = BoardCache.query.filter_by(user_id=current_user.id).all()
    if cached:
        return jsonify({"boards": [b.to_dict() for b in cached]})

    # Fetch fresh from Pinterest
    token = pinterest_service.ensure_valid_token(current_user)
    if not token:
        return jsonify({"error": "Invalid Pinterest token", "boards": []}), 401

    try:
        fresh_boards = pinterest_service.get_boards(token)
    except Exception as exc:
        return jsonify({"error": str(exc), "boards": []}), 502

    # Cache results
    BoardCache.query.filter_by(user_id=current_user.id).delete()
    for b in fresh_boards:
        db.session.add(BoardCache(
            user_id=current_user.id,
            board_id=b["id"],
            board_name=b["name"],
            board_description=b.get("description", ""),
            board_image_url=b.get("image_url"),
            pin_count=b.get("pin_count", 0),
        ))
    db.session.commit()

    return jsonify({"boards": fresh_boards})


@api_bp.route("/boards/refresh", methods=["POST"])
@login_required
def refresh_boards():
    """Force-clear the board cache so next /api/boards returns fresh data."""
    BoardCache.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"success": True})


# ── /api/history ──────────────────────────────────────────────────────────────

@api_bp.route("/history", methods=["GET"])
@login_required
def history():
    """Return the last 50 pins for the current user."""
    pins = current_user.recent_pins(limit=50)
    return jsonify({"pins": [p.to_dict() for p in pins]})


@api_bp.route("/history/<int:pin_id>", methods=["DELETE"])
@login_required
def delete_pin(pin_id: int):
    """Delete a specific pin from the current user's history."""
    pin = Pin.query.filter_by(id=pin_id, user_id=current_user.id).first_or_404()
    db.session.delete(pin)
    db.session.commit()
    return jsonify({"success": True})
