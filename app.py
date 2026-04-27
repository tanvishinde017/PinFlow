from flask import Flask, render_template, request
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_ai_content(link):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Generate Pinterest title, description and hashtags for {link}"
            }]
        )
        return response.choices[0].message.content
    except Exception as e:
        return str(e)


# FAKE IMAGE FETCH (for now)
def get_images():
    return [
        "https://via.placeholder.com/300",
        "https://via.placeholder.com/301",
        "https://via.placeholder.com/302"
    ]


@app.route("/", methods=["GET", "POST"])
def index():
    images = []
    data = None

    if request.method == "POST":
        link = request.form.get("link")
        action = request.form.get("action")

        if action == "fetch":
            images = get_images()

        if action == "generate":
            selected_image = request.form.get("selected_image")
            content = generate_ai_content(link)

            data = {
                "image": selected_image,
                "content": content,
                "link": link
            }

    return render_template("index.html", images=images, data=data)


if __name__ == "__main__":
    app.run(debug=True)