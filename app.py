from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os
import json
from datetime import datetime
from PIL import Image
from io import BytesIO

app = Flask(__name__)

# storage
HISTORY_FILE = "history.json"
IMAGE_FOLDER = "static/downloads"

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# -----------------------------
# UTIL: Save history
# -----------------------------
def save_history(data):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)

    history.append(data)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-20:], f, indent=2)


# -----------------------------
# AMAZON SCRAPER (IMPROVED)
# -----------------------------
def get_product_data(link):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        }

        r = requests.get(link, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")

        title = soup.find(id="productTitle")
        price = soup.find("span", {"class": "a-offscreen"})

        title = title.get_text(strip=True) if title else "Trending Product"
        price = price.get_text(strip=True) if price else "N/A"

        img = soup.find(id="landingImage")
        image = img.get("src") if img else None

        return {
            "title": title,
            "price": price,
            "image": image
        }

    except:
        return {"title": "Trending Product", "price": "N/A", "image": None}


# -----------------------------
# SMART KEYWORDS (UPGRADED)
# -----------------------------
def extract_keywords(title):
    words = re.findall(r"[A-Za-z]{4,}", title)
    return list(dict.fromkeys(words))[:6]


# -----------------------------
# AI CONTENT (BETTER)
# -----------------------------
def generate_content(title):
    keywords = extract_keywords(title)

    title_out = "🔥 " + " ".join(keywords[:4])

    description = (
        f"✨ Upgrade your lifestyle with this {keywords[0]}! "
        f"Perfect for daily use, trending right now 🚀 "
        f"Don’t miss out — limited availability!"
    )

    hashtags = " ".join([f"#{k.lower()}" for k in keywords])
    hashtags += " #amazonfinds #trending #viral #musthave"

    return {
        "title": title_out,
        "description": description,
        "hashtags": hashtags
    }


# -----------------------------
# DOWNLOAD IMAGE
# -----------------------------
def download_image(url):
    try:
        r = requests.get(url)
        img = Image.open(BytesIO(r.content))

        filename = f"{datetime.now().timestamp()}.jpg"
        path = os.path.join(IMAGE_FOLDER, filename)

        img.save(path)

        return "/" + path
    except:
        return None


# -----------------------------
# GENERATE RANDOM IMAGES
# -----------------------------
def get_images():
    return [f"https://picsum.photos/400/600?random={i}" for i in range(6)]


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/fetch", methods=["POST"])
def fetch():
    link = request.json.get("link")

    product = get_product_data(link)
    images = get_images()

    return jsonify({
        "title": product["title"],
        "price": product["price"],
        "product_image": product["image"],
        "images": images,
        "link": link
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json

    content = generate_content(data["title"])

    saved_img = download_image(data["selected_image"])

    result = {
        "title": content["title"],
        "description": content["description"],
        "hashtags": content["hashtags"],
        "image": saved_img or data["selected_image"],
        "link": data["link"],
        "created_at": str(datetime.now())
    }

    save_history(result)

    return jsonify(result)


@app.route("/api/history")
def history():
    if not os.path.exists(HISTORY_FILE):
        return jsonify([])

    with open(HISTORY_FILE) as f:
        return jsonify(json.load(f))


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)