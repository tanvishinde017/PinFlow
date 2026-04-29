from flask import Flask, render_template, request
import requests

app = Flask(__name__)


# 🔥 AI (OLLAMA)
def generate_ai_content(link):
    try:
        prompt = f"""
        You are a professional Pinterest marketer.

        Generate HIGH QUALITY content.

        Rules:
        - Title: catchy, max 8 words
        - Description: 1-2 short lines, engaging
        - Tags: exactly 5 trending hashtags

        Product: {link}

        STRICT FORMAT:
        Title: ...
        Description: ...
        Tags: ...
        """

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 120
                }
            }
        )

        text = response.json().get("response", "")

        # ✅ SAFE PARSING
        title = ""
        description = ""
        tags = ""

        for line in text.split("\n"):
            if "Title:" in line:
                title = line.replace("Title:", "").strip()
            elif "Description:" in line:
                description = line.replace("Description:", "").strip()
            elif "Tags:" in line:
                tags = line.replace("Tags:", "").strip()

        return {
            "title": title or "🔥 Trending Product",
            "description": description or "Check this amazing product!",
            "tags": tags or "#trending #shopping #deal #amazon #viral"
        }

    except Exception as e:
        return {
            "title": "Error",
            "description": str(e),
            "tags": ""
        }


# 🖼️ IMAGE FETCH (keyword based)
def get_images(link):
    try:
        keyword = link.split("/")[-1]
        keyword = keyword.replace("-", " ")

        return [
            f"https://source.unsplash.com/300x300/?{keyword}",
            f"https://source.unsplash.com/301x301/?{keyword}",
            f"https://source.unsplash.com/302x302/?{keyword}"
        ]

    except:
        return [
            "https://picsum.photos/300",
            "https://picsum.photos/301",
            "https://picsum.photos/302"
        ]


# 🌐 MAIN ROUTE (FIXED)
@app.route("/", methods=["GET", "POST"])
def index():
    images = []
    data = None
    link = ""

    if request.method == "POST":
        link = request.form.get("link")
        action = request.form.get("action")

        if action == "fetch":
            images = get_images(link)

        elif action == "generate":
            selected_image = request.form.get("selected_image")
            content = generate_ai_content(link)

            data = {
                "image": selected_image,
                "title": content["title"],
                "description": content["description"],
                "tags": content["tags"],
                "link": link
            }

            images = get_images(link)  # keep images visible

    return render_template("index.html", images=images, data=data, link=link)


if __name__ == "__main__":
    app.run(debug=True)