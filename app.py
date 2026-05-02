from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

app = Flask(__name__)

# -----------------------------
# Extract product data from Amazon
# -----------------------------
def get_product_data(link):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

        response = requests.get(link, headers=headers, timeout=12)
        soup = BeautifulSoup(response.content, "html.parser")

        # Title
        title_tag = soup.find(id="productTitle")
        title = title_tag.get_text().strip() if title_tag else "Trending Product"

        # Product image
        image = None
        img_tag = soup.find(id="landingImage") or soup.find(id="imgBlkFront")
        if img_tag:
            image = img_tag.get("src") or img_tag.get("data-old-hires") or img_tag.get("data-a-dynamic-image")
            if isinstance(image, str) and image.startswith("{"):
                # data-a-dynamic-image is a JSON dict of {url: [w,h]}
                import json
                try:
                    img_dict = json.loads(image)
                    image = max(img_dict, key=lambda u: img_dict[u][0])
                except Exception:
                    image = None

        return {"title": title, "image": image}

    except Exception:
        return {"title": "Trending Product", "image": None}


# -----------------------------
# Smart keyword extraction
# -----------------------------
def extract_keywords(title):
    stopwords = {
        "with", "for", "and", "the", "in", "of", "to", "a", "an",
        "by", "at", "from", "on", "is", "it", "or", "as", "be",
        "up", "set", "pack", "piece", "count", "new", "best", "top",
        "premium", "high", "quality", "ultra", "super", "pro", "plus",
        "mini", "max", "xl", "large", "small", "black", "white", "red",
        "blue", "green", "pink", "2", "3", "4", "5", "6", "10", "12",
        "inch", "inches", "cm", "mm", "ft", "lbs", "oz", "kg", "g"
    }
    words = re.findall(r"[A-Za-z]{3,}", title)
    keywords = [w for w in words if w.lower() not in stopwords]
    return keywords[:5]


# -----------------------------
# Generate hashtags
# -----------------------------
def generate_hashtags(keywords, category_hint=""):
    base = ["#amazon", "#shopping", "#musthave", "#deals", "#onlineshopping"]
    kw_tags = [f"#{k.lower()}" for k in keywords[:5]]
    extra = ["#trending", "#viral", "#lifestyle", "#newarrival", "#sale"]
    all_tags = list(dict.fromkeys(kw_tags + base + extra))
    return " ".join(all_tags[:12])


# -----------------------------
# Generate pin content
# -----------------------------
def generate_content(title):
    keywords = extract_keywords(title)
    keyword_str = " ".join(keywords[:3])

    short_title = title[:80] + ("..." if len(title) > 80 else "")

    description = (
        f"✨ Discover the {keywords[0] if keywords else 'amazing'} everyone is talking about! "
        f"This {keyword_str} is a total game-changer — perfect for gifting, everyday use, or treating yourself. "
        f"Shop now before it sells out! 🛒💫"
    )

    hashtags = generate_hashtags(keywords)

    return {
        "title": short_title,
        "description": description,
        "hashtags": hashtags,
    }


# -----------------------------
# Fetch images from Unsplash
# -----------------------------
def get_images(title):
    keywords = extract_keywords(title)
    query = "+".join(keywords[:3]) if keywords else "product"

    # Use different seeds/sizes to get varied results
    sizes = [
        ("400", "600"),
        ("400", "500"),
        ("400", "650"),
        ("400", "550"),
        ("400", "700"),
        ("400", "480"),
    ]
    images = []
    for i, (w, h) in enumerate(sizes):
        url = f"https://picsum.photos/{w}/{h}?random={i}"
        images.append(url)
    return images


# -----------------------------
# Main route (renders page)
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


# -----------------------------
# AJAX: Fetch product data + images
# -----------------------------
@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    body = request.get_json()
    link = (body or {}).get("link", "").strip()

    if not link:
        return jsonify({"error": "No link provided"}), 400

    product = get_product_data(link)
    images = get_images(product["title"])

    return jsonify({
        "title": product["title"],
        "product_image": product["image"],
        "images": images,
        "link": link,
    })


# -----------------------------
# AJAX: Generate pin content
# -----------------------------
@app.route("/api/generate", methods=["POST"])
def api_generate():
    body = request.get_json()
    title = (body or {}).get("title", "Trending Product")
    selected_image = (body or {}).get("selected_image", "")
    link = (body or {}).get("link", "")

    content = generate_content(title)

    return jsonify({
        "title": content["title"],
        "description": content["description"],
        "hashtags": content["hashtags"],
        "image": selected_image,
        "link": link,
    })


# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)