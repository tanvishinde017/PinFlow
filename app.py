from flask import Flask, render_template, request
import random

app = Flask(__name__)

def generate_content(link):
    titles = [
        "🔥 Trending Product You Must Try!",
        "💡 Smart Buy You’ll Love",
        "🛒 Best Deal on Amazon Right Now",
        "✨ Upgrade Your Lifestyle Today"
    ]

    descriptions = [
        "This product is gaining massive popularity. Perfect for daily use and highly rated!",
        "One of the best finds online right now. Worth every penny.",
        "People are loving this product for its quality and performance.",
    ]

    hashtags = "#amazonfinds #trending #musthave #deals #shopping"

    return random.choice(titles), random.choice(descriptions), hashtags

@app.route("/", methods=["GET", "POST"])
def index():
    data = None

    if request.method == "POST":
        link = request.form["link"]
        image = request.form["image"]

        title, desc, tags = generate_content(link)

        data = {
            "link": link,
            "image": image,
            "title": title,
            "desc": desc,
            "tags": tags
        }

    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)