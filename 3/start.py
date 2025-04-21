from flask import Flask, request, Response, send_file, jsonify
import requests
import threading
import webbrowser
import os

app = Flask(__name__)

# Serve frontend files
@app.route("/")
def index():
    return send_file("index.html")

@app.route("/style.css")
def style():
    return send_file("style.css")

@app.route("/script.js")
def script():
    return send_file("script.js")

@app.route("/favicon.ico")
def favicon():
    return "", 204

# Model list proxy
@app.route("/proxy/models")
def proxy_models():
    try:
        res = requests.get("https://freerouter.cablyai.com/v1/models")
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Stream response proxy
@app.route("/v1/completions", methods=["POST"])
def stream_completions():
    payload = request.get_json()

    def generate():
        try:
            with requests.post(
                "https://freerouter.cablyai.com/v1/chat/completions",
                json=payload,
                headers={"Accept": "text/event-stream", "Content-Type": "application/json"},
                stream=True
            ) as r:
                for line in r.iter_lines():
                    if line:
                        yield f"data: {line.decode('utf-8')}\r\n"
                yield "data: [DONE]\r\n"
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\r\n"

    return Response(generate(), content_type="text/event-stream")

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1, open_browser).start()
    app.run(debug=True)
