from flask import Flask, render_template, request
import json
import base64
from datetime import datetime
from openai import OpenAI  # make sure you have the OpenAI client installed and configured

app = Flask(__name__)

# Load models from beta.json
with open("beta.json", "r") as f:
    beta_data = json.load(f)
    models = [model["id"] for model in beta_data["data"]]

# ====================== API CONFIGURATION ======================
API_KEY = "ddc-beta-owt4ux3idq-aVQGkekXPETsicuyoDq8Ub6Heww0zoMVYva"
BASE_URL = "https://beta.sree.shop/v1"

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

@app.route("/", methods=["GET", "POST"])
def index():
    response_text = ""
    user_message = ""
    stream_enabled = False
    image_generation = False

    if request.method == "POST":
        user_message = request.form.get("message", "")
        stream_enabled = request.form.get("stream") == "on"
        image_generation = request.form.get("image") == "on"
        selected_model = request.form.get("model")
        
        # If image generation is selected, use the image API
        if image_generation:
            prompt = user_message if user_message else "A beautiful scenery"
            try:
                image_response = client.images.generate(
                    model=selected_model,
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                    response_format="b64_json"
                )
                image_data = image_response.data[0].b64_json
                # Save the image locally
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_filename = f"generated_image_{timestamp}.png"
                with open(image_filename, "wb") as image_file:
                    image_file.write(base64.b64decode(image_data))
                response_text = f"✅ Image generated and saved as: {image_filename}"
            except Exception as e:
                response_text = f"Error during image generation: {str(e)}"
        
        # Otherwise, use chat completions
        else:
            try:
                if stream_enabled:
                    # Streaming chat completion
                    messages = [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": user_message}
                    ]
                    stream = client.chat.completions.create(
                        model=selected_model,
                        messages=messages,
                        stream=True
                    )
                    chat_response = ""
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            chat_response += chunk.choices[0].delta.content
                    response_text = chat_response.strip()
                else:
                    # Standard (non-streaming) chat completion
                    messages = [
                        {"role": "user", "content": user_message}
                    ]
                    chat_resp = client.chat.completions.create(
                        model=selected_model,
                        messages=messages,
                        stream=False
                    )
                    response_text = str(chat_resp)
            except Exception as e:
                response_text = f"Error during chat completion: {str(e)}"
    
    return render_template(
        "index.html",
        models=models,
        response=response_text,
        user_message=user_message,
        stream=stream_enabled,
        image=image_generation
    )

if __name__ == "__main__":
    app.run(debug=True)
