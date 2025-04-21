import base64
import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, request, jsonify, g, render_template, Response, stream_with_context
from openai import OpenAI

# ====================== API CONFIGURATION ======================
API_KEY = "ddc-beta-owt4ux3idq-aVQGkekXPETsicuyoDq8Ub6Heww0zoMVYva"
BASE_URL = "https://beta.sree.shop/v1"
 
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

app = Flask(__name__, template_folder='templates')
DATABASE = 'chathistory.db'
os.makedirs('images', exist_ok=True)

# Load available models from beta.json
with open("beta.json", "r") as f:
    beta_data = json.load(f)
    models = [model["id"] for model in beta_data["data"]]

# Split models into categories:
# - Image models: names containing "flux"
# - Thinking models: names containing "thinking"
# - Text models: all remaining models.
image_models = [m for m in models if "flux" in m.lower()]
thinking_models = [m for m in models if "thinking" in m.lower()]
text_models = [m for m in models if ("flux" not in m.lower())]

# ============== DATABASE SETUP ==============
def get_db():
    """Creates a database connection."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection when the app context ends."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        
def init_db():
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        # auto‑add image_data if missing
        cursor.execute("PRAGMA table_info(images)")
        existing = [r[1] for r in cursor.fetchall()]
        if existing and 'image_data' not in existing:
            cursor.execute("ALTER TABLE images ADD COLUMN image_data TEXT;")

        # (Re‑)create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                input_text TEXT,
                output_text TEXT,
                is_image_request INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                image_data TEXT,
                FOREIGN KEY (chat_id) REFERENCES chats (id)
            )
        ''')
        db.commit()

# ============== ROUTES ==============
@app.route('/')
def index():
    """Renders the HTML page."""
    return render_template("index.html",
                           text_models=text_models,
                           image_models=image_models,
                           thinking_models=thinking_models)

@app.route('/process_request', methods=['POST'])
def process_request():
    """Handles non-streaming chat or image generation requests."""
    data = request.json
    user_input = data.get('input', '').strip()
    stream_enabled = data.get('stream', False)
    selected_text_model = data.get('text_model')
    selected_image_model = data.get('image_model')

    if user_input.lower().startswith('-img'):
        prompt = user_input[4:].strip()  # Remove the -img prefix
        return handle_image_generation(prompt, user_input, selected_image_model)
    
    # Fallback to chat for non-streaming mode
    return handle_chat_completion(user_input, selected_text_model, stream=False)

@app.route('/stream', methods=['GET'])
def stream():
    """Dedicated endpoint for server-sent events (SSE) streaming."""
    prompt = request.args.get('input', '')
    model = request.args.get('model')
    
    def generate():
        try:
            text_model = model if model else (text_models[0] if text_models else "Provider-5/qwen-2.5-coder-32b")
            
            stream = client.chat.completions.create(
                model=text_model,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            
            print("📊 Streaming Response:")
            readable_response = ""
            for chunk in stream:
                # Safely extract content without index error
                delta = ""
                if getattr(chunk, "choices", None):
                    choice = chunk.choices[0]
                    if getattr(choice, "delta", None) and choice.delta.content:
                        delta = choice.delta.content
                readable_response += delta
                yield f"data: {delta}\n\n"  # SSE format
            
            # Save full response to DB
            save_chat_to_db(prompt, readable_response.strip(), False)
            
        except Exception as e:
            error_message = f"Error processing stream request: {str(e)}"
            save_chat_to_db(prompt, error_message, False)
            yield f"data: {error_message}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    """Fetches chat history from the database."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
    SELECT c.id, c.timestamp, c.input_text, c.output_text, c.is_image_request
    FROM chats c
    ORDER BY c.id DESC
    LIMIT 50
    ''')
    chats = []
    for row in cursor.fetchall():
        chat = {
            'id': row['id'],
            'timestamp': row['timestamp'],
            'input_text': row['input_text'],
            'output_text': row['output_text'],
            'is_image_request': bool(row['is_image_request']),
            'images': []
        }
        if chat['is_image_request']:
            img_cursor = db.cursor()
            img_cursor.execute('SELECT image_data FROM images WHERE chat_id = ?', (chat['id'],))
            chat['images'] = [img_row['image_data'] for img_row in img_cursor.fetchall()]
        chats.append(chat)
    return jsonify(chats)

# ============== DATABASE STORAGE ==============
def save_chat_to_db(input_text, output_text, is_image_request, image_datas=None):
    """Saves the chat or image request to the database."""
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
        INSERT INTO chats (timestamp, input_text, output_text, is_image_request)
        VALUES (?, ?, ?, ?)
        ''', (timestamp, input_text, output_text, 1 if is_image_request else 0))
        chat_id = cursor.lastrowid
        if image_datas:
            for data in image_datas:
                cursor.execute('''
                INSERT INTO images (chat_id, image_data)
                VALUES (?, ?)
                ''', (chat_id, data))
        db.commit()
        return chat_id

# ============== IMAGE GENERATION ==============
def handle_image_generation(prompt, original_input, model):
    """Handles image generation using the selected image model.
       Returns a data URI for the image instead of a path.
    """
    try:
        image_model = model if model else (image_models[0] if image_models else "Provider-5/flux-schnell")
        response = client.images.generate(
            model=image_model,
            prompt=prompt,
           n=1,  # Number of images to generate
            size="1024x1024",
            response_format="b64_json"
        )
        image_datas = []
        for i, image_data in enumerate(response.data):
            # Create a data URI from the base64 encoded string
            data_uri = "data:image/png;base64," + image_data.b64_json
            image_datas.append(data_uri)
        output_text = f"✅ Generated {len(image_datas)} image(s) with model: {image_model}"
        save_chat_to_db(original_input, output_text, True, image_datas)
        return jsonify({"output": output_text, "images": image_datas})
    except Exception as e:
        error_message = f"Error generating images: {str(e)}"
        save_chat_to_db(original_input, error_message, True)
        return jsonify({"output": error_message, "images": []})

# ============== CHAT COMPLETION ==============
def handle_chat_completion(prompt, model, stream_enabled):
    """Handles chat responses using the selected text model."""
    try:
        text_model = model if model else (text_models[0] if text_models else "Provider-5/qwen-2.5-coder-32b")

        if stream_enabled:
            def generate():
                stream = client.chat.completions.create(
                    model=text_model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True
                )
                print("📊 Streaming Response:")
                readable_response = ""
                for chunk in stream:
                    # Safely extract content without index error
                    delta = ""
                    if getattr(chunk, "choices", None):
                        choice = chunk.choices[0]
                        if getattr(choice, "delta", None) and choice.delta.content:
                            delta = choice.delta.content
                    readable_response += delta
                    yield f"data: {delta}\n\n"  # SSE format

                # Save full response to DB
                save_chat_to_db(prompt, readable_response.strip(), False)

            return Response(stream_with_context(generate()), mimetype='text/event-stream')

        else:
            response = client.chat.completions.create(
                model=text_model,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            chat_response = response.choices[0].message.content
            save_chat_to_db(prompt, chat_response, False)
            return jsonify({"output": chat_response})

    except Exception as e:
        error_message = f"Error processing request: {str(e)}"
        save_chat_to_db(prompt, error_message, False)
        return jsonify({"output": error_message})


# ============== APP START ==============
if __name__ == '__main__':
    init_db()  # Initialize the database before starting the Flask app
    app.run(debug=True, port=5000)