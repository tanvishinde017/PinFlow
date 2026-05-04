"""
PinFlow AI — Database Models
Defines User, Pin, and BoardCache with relationships.
"""

from datetime import datetime
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    """Registered user with optional Pinterest OAuth tokens."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Pinterest OAuth
    pinterest_access_token = db.Column(db.Text, nullable=True)
    pinterest_refresh_token = db.Column(db.Text, nullable=True)
    pinterest_token_expires_at = db.Column(db.DateTime, nullable=True)
    pinterest_user_id = db.Column(db.String(128), nullable=True)
    pinterest_username = db.Column(db.String(128), nullable=True)

    # Relationships
    pins = db.relationship("Pin", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    board_caches = db.relationship("BoardCache", backref="owner", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_pinterest_connected(self) -> bool:
        return bool(self.pinterest_access_token)

    def recent_pins(self, limit: int = 50):
        return self.pins.order_by(Pin.created_at.desc()).limit(limit).all()


class Pin(db.Model):
    """A generated Pinterest pin (draft or posted)."""

    __tablename__ = "pins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Content
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    hashtags = db.Column(db.Text, nullable=True)
    cta = db.Column(db.String(255), nullable=True)
    tone = db.Column(db.String(64), default="viral")

    # Media & Link
    image_url = db.Column(db.Text, nullable=True)
    affiliate_link = db.Column(db.Text, nullable=True)

    # Pinterest destination
    board_id = db.Column(db.String(255), nullable=True)
    board_name = db.Column(db.String(255), nullable=True)
    pinterest_pin_id = db.Column(db.String(255), nullable=True)  # ID returned after posting

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(
        db.String(32),
        default="draft",
        nullable=False,
    )  # draft | posted | failed

    # Raw product data (stored as JSON text for reference)
    product_title = db.Column(db.Text, nullable=True)
    product_price = db.Column(db.String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<Pin {self.id} [{self.status}] {self.title[:40]}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "hashtags": self.hashtags,
            "cta": self.cta,
            "tone": self.tone,
            "image_url": self.image_url,
            "affiliate_link": self.affiliate_link,
            "board_id": self.board_id,
            "board_name": self.board_name,
            "pinterest_pin_id": self.pinterest_pin_id,
            "status": self.status,
            "product_title": self.product_title,
            "product_price": self.product_price,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BoardCache(db.Model):
    """Cached Pinterest boards for a user to avoid repeated API calls."""

    __tablename__ = "board_caches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    board_id = db.Column(db.String(255), nullable=False)
    board_name = db.Column(db.String(255), nullable=False)
    board_description = db.Column(db.Text, nullable=True)
    board_image_url = db.Column(db.Text, nullable=True)
    pin_count = db.Column(db.Integer, default=0)

    cached_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<BoardCache {self.board_name}>"

    def to_dict(self) -> dict:
        return {
            "id": self.board_id,
            "name": self.board_name,
            "description": self.board_description,
            "image_url": self.board_image_url,
            "pin_count": self.pin_count,
        }
