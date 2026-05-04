"""
PinFlow AI — Celery Background Tasks
Handles async Pinterest posting with automatic retry on failure.
"""

from app import celery, db
from app.models import Pin, User
from app.services import pinterest_service


@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,  # seconds between retries
    name="tasks.post_pin_to_pinterest",
)
def post_pin_to_pinterest(self, pin_id: int) -> dict:
    """
    Background task: post a saved Pin to Pinterest.

    Retries up to 3 times with 30-second delays on transient errors.
    Updates Pin.status to 'posted' or 'failed' upon completion.

    Args:
        pin_id: Primary key of the Pin record to post.
    """
    pin = Pin.query.get(pin_id)
    if not pin:
        return {"success": False, "error": f"Pin {pin_id} not found"}

    user = User.query.get(pin.user_id)
    if not user:
        pin.status = "failed"
        db.session.commit()
        return {"success": False, "error": "User not found"}

    # Ensure we have a valid (possibly refreshed) access token
    access_token = pinterest_service.ensure_valid_token(user)
    if not access_token:
        pin.status = "failed"
        db.session.commit()
        return {"success": False, "error": "No valid Pinterest token"}

    try:
        result = pinterest_service.post_pin(
            access_token=access_token,
            board_id=pin.board_id,
            title=pin.title,
            description=f"{pin.description}\n\n{pin.hashtags}",
            image_url=pin.image_url,
            link=pin.affiliate_link,
        )

        pin.status = "posted"
        pin.pinterest_pin_id = result.get("id")
        db.session.commit()

        return {"success": True, "pinterest_pin_id": pin.pinterest_pin_id}

    except Exception as exc:
        print(f"[celery] post_pin_to_pinterest failed for pin {pin_id}: {exc}")

        # Retry on transient errors; mark failed after exhausting retries
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            pin.status = "failed"
            db.session.commit()
            return {"success": False, "error": str(exc)}
