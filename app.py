from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)


# -----------------------------
# Get product title from Amazon
# -----------------------------
def get_product_data(link):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(link, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        title = soup.find(id="productTitle")

        if title:
            return title.get_text().strip()

        return "Trending Product"

    except Exception:
        return "Trending Product"


# -----------------------------
# Generate placeholder content
# -----------------------------
def generate_content(title):
    return {
        "title": title,
        "description": f"🔥 Check out this amazing product: {title}",
        "tags": "#amazon #shopping #deal #trending #viral"
    }


# -----------------------------
# Fetch matching images
# -----------------------------
def get_images_from_title(title):
    keyword = " ".join(title.split()[:3])

    return [
        f"https://source.unsplash.com/300x300/?{keyword}",
        f"https://source.unsplash.com/301x301/?{keyword}",
        f"https://source.unsplash.com/302x302/?{keyword}"
    ]


# -----------------------------
# Main route
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    images = []
    data = None
    link = ""

    if request.method == "POST":
        link = request.form.get("link")
        action = request.form.get("action")

        title = get_product_data(link)

        if action == "fetch":
            images = get_images_from_title(title)

        elif action == "generate":
            selected_image = request.form.get("selected_image")

            content = generate_content(title)

            data = {
                "image": selected_image,
                "title": content["title"],
                "description": content["description"],
                "tags": content["tags"],
                "link": link
            }

            images = get_images_from_title(title)

    return render_template(
        "index.html",
        images=images,
        data=data,
        link=link
    )


# -----------------------------
# Run app
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)