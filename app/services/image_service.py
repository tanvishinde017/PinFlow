"""
PinFlow AI — Image Service
Downloads and stores images locally, returning a web-accessible path.
"""

import os
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
from flask import current_app


def download_and_save(url: str) -> str | None:
    """
    Download an image from a URL, convert to RGB JPEG, save to UPLOAD_FOLDER.

    Returns:
        Web path string like '/static/downloads/1234567890.jpg',
        or None on failure.
    """
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()

        img = Image.open(BytesIO(resp.content)).convert("RGB")

        filename = f"{int(datetime.utcnow().timestamp() * 1000)}.jpg"
        folder = current_app.config["UPLOAD_FOLDER"]
        save_path = os.path.join(folder, filename)
        img.save(save_path, format="JPEG", quality=92, optimize=True)

        # Return the path relative to the static root so it can be served
        return f"/static/downloads/{filename}"

    except Exception as exc:
        print(f"[image_service] Failed to download {url}: {exc}")
        return None
