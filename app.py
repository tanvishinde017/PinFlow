from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os
import json
from datetime import datetime
from PIL import Image
from io import BytesIO
import anthropic

app = Flask(__name__)

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
HISTORY_FILE = "history.json"
IMAGE_FOLDER = "static/downloads"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Anthropic client — reads ANTHROPIC_API_KEY from env automatically
ai_client = anthropic.Anthropic()


# ─────────────────────────────
# UTIL: Save / Load history
# ─────────────────────────────
def save_history(data):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    history.append(data)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-50:], f, indent=2)


# ─────────────────────────────
# AMAZON SCRAPER
# ─────────────────────────────
def get_product_data(link):
    """Scrape title, price, and hero image from an Amazon product page."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        r = requests.get(link, headers=headers, timeout=12)
        soup = BeautifulSoup(r.content, "html.parser")

        title_el = soup.find(id="productTitle")
        price_el = soup.find("span", {"class": "a-offscreen"})
        img_el = soup.find(id="landingImage")

        title = title_el.get_text(strip=True) if title_el else "Trending Product"
        price = price_el.get_text(strip=True) if price_el else "N/A"
        image = img_el.get("src") if img_el else None

        # Try data-old-hires for higher-res image
        if img_el and img_el.get("data-old-hires"):
            image = img_el["data-old-hires"]

        return {"title": title, "price": price, "image": image}

    except Exception as e:
        print(f"[scraper error] {e}")
        return {"title": "Trending Product", "price": "N/A", "image": None}


# ─────────────────────────────
# AI CONTENT via Claude
# ─────────────────────────────
def generate_content_ai(title: str, price: str, tone: str = "viral") -> dict:
    """
    Use Claude to generate Pinterest-optimised title, description, and hashtags.
    tone: 'viral' | 'luxury' | 'casual' | 'affiliate'
    """
    tone_guide = {
        "viral":     "energetic, hype-driven, uses emojis, FOMO-inducing",
        "luxury":    "elegant, aspirational, refined, minimal emoji, prestige-focused",
        "casual":    "friendly, conversational, relatable, light emoji use",
        "affiliate": "benefit-focused, call-to-action heavy, discount/deal-oriented",
    }
    style = tone_guide.get(tone, tone_guide["viral"])

    prompt = f"""You are a Pinterest marketing expert. 
Given this Amazon product, create Pinterest content in a {tone} tone ({style}).

Product title: {title}
Price: {price}

Return ONLY valid JSON (no markdown, no explanation) with exactly these keys:
{{
  "pin_title": "...",          // max 100 chars, catchy
  "description": "...",        // 150-200 chars, engaging
  "hashtags": "...",           // 10-15 hashtags as a single string
  "cta": "..."                 // short call-to-action phrase, max 10 words
}}"""

    message = ai_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw)


# ─────────────────────────────
# MULTI-VARIATION GENERATION
# ─────────────────────────────
def generate_variations(title: str, price: str) -> list:
    """Generate A/B content variations across all tones."""
    tones = ["viral", "luxury", "casual", "affiliate"]
    results = []
    for tone in tones:
        try:
            content = generate_content_ai(title, price, tone)
            content["tone"] = tone
            results.append(content)
        except Exception as e:
            print(f"[variation error: {tone}] {e}")
    return results


# ─────────────────────────────
# IMAGE UTILS
# ─────────────────────────────
def get_lifestyle_images(keywords: list) -> list:
    """Return curated Unsplash-style images based on product keywords."""
    seeds = [abs(hash(k)) % 1000 for k in keywords[:3]] or [42, 73, 99]
    images = []
    for i, seed in enumerate(seeds * 3):
        images.append(f"https://picsum.photos/seed/{seed + i}/600/800")
    return images[:9]


def download_image(url: str) -> str | None:
    """Download and save an image locally, return its web path."""
    try:
        r = requests.get(url, timeout=10)
        img = Image.open(BytesIO(r.content)).convert("RGB")
        filename = f"{int(datetime.now().timestamp() * 1000)}.jpg"
        path = os.path.join(IMAGE_FOLDER, filename)
        img.save(path, quality=90)
        return "/" + path
    except Exception as e:
        print(f"[image download error] {e}")
        return None


# ─────────────────────────────
# ROUTES
# ─────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/fetch", methods=["POST"])
def fetch():
    """Scrape an Amazon product link and return metadata + image options."""
    link = request.json.get("link", "").strip()
    if not link:
        return jsonify({"error": "No link provided"}), 400

    product = get_product_data(link)

    # Extract keywords for image search seeds
    keywords = re.findall(r"[A-Za-z]{4,}", product["title"])[:6]
    lifestyle_images = get_lifestyle_images(keywords)

    return jsonify({
        "title":          product["title"],
        "price":          product["price"],
        "product_image":  product["image"],
        "images":         lifestyle_images,
        "link":           link,
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    """Generate AI Pinterest content for a product."""
    data = request.json
    title  = data.get("title", "")
    price  = data.get("price", "N/A")
    tone   = data.get("tone", "viral")

    try:
        content = generate_content_ai(title, price, tone)
    except Exception as e:
        print(f"[AI error] {e}")
        # Graceful fallback
        content = {
            "pin_title":   f"🔥 {title[:80]}",
            "description": f"✨ This {title.split()[0]} is trending! Perfect for every lifestyle. Don't miss out!",
            "hashtags":    "#amazonfinds #trending #viral #musthave #deals",
            "cta":         "Shop now before it's gone!",
        }

    return jsonify({**content, "tone": tone})


@app.route("/api/variations", methods=["POST"])
def variations():
    """Generate content in all 4 tones for A/B testing."""
    data  = request.json
    title = data.get("title", "")
    price = data.get("price", "N/A")

    results = generate_variations(title, price)
    return jsonify({"variations": results})


@app.route("/api/save", methods=["POST"])
def save():
    """Save a completed pin to history."""
    data = request.json

    selected_img = data.get("selected_image")
    saved_img    = download_image(selected_img) if selected_img else None

    result = {
        "pin_title":    data.get("pin_title", ""),
        "description":  data.get("description", ""),
        "hashtags":     data.get("hashtags", ""),
        "cta":          data.get("cta", ""),
        "tone":         data.get("tone", "viral"),
        "image":        saved_img or selected_img,
        "link":         data.get("link", ""),
        "created_at":   str(datetime.now()),
    }

    save_history(result)
    return jsonify({"success": True, "pin": result})


@app.route("/api/history")
def history():
    """Return the last 50 saved pins."""
    if not os.path.exists(HISTORY_FILE):
        return jsonify([])
    with open(HISTORY_FILE) as f:
        return jsonify(json.load(f))


@app.route("/api/history/<int:index>", methods=["DELETE"])
def delete_history_item(index):
    """Delete a specific pin from history by index."""
    if not os.path.exists(HISTORY_FILE):
        return jsonify({"error": "No history"}), 404
    with open(HISTORY_FILE) as f:
        history = json.load(f)
    if index < 0 or index >= len(history):
        return jsonify({"error": "Invalid index"}), 400
    history.pop(index)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
    return jsonify({"success": True})


# ─────────────────────────────
# RUN
# ─────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)