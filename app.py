from flask import Flask, render_template, request
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_ai_content(link):
    prompt = f"""
    Generate Pinterest content for this product: {link}

    Give:
    1. Catchy Title
    2. Engaging Description
    3. 5 Trending Hashtags
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content

    return content

@app.route("/", methods=["GET", "POST"])
def index():
    data = None

    if request.method == "POST":
        link = request.form["link"]
        image = request.form["image"]

        ai_content = generate_ai_content(link)

        data = {
            "link": link,
            "image": image,
            "content": ai_content
        }

    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)