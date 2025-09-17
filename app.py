import os
from datetime import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)

# Allow CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Mongo connection
MONGO_URI = os.getenv("MONGO_URI") or "mongodb+srv://admin:ahmad@cluster0.oyvzkiz.mongodb.net/test?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["test"]  # use your existing "test" database

# Users collection
users = db["users"]


@app.route("/login", methods=["POST"])
def login():
    """
    Login check
    """
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "Missing username/password"}), 400

    user = users.find_one({"username": username, "password": password})
    if user:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})


@app.route("/api/event", methods=["POST", "OPTIONS"])
def log_event():
    if request.method == "OPTIONS":
        return _build_cors_prelight_response()

    data = request.json or {}
    username = data.get("username")
    event = data.get("event")

    if not username or not event:
        return jsonify({"success": False, "error": "Missing username or event"}), 400

    logs.insert_one({
        "username": username,
        "event": event,
        "timestamp": datetime.utcnow()
    })

    return jsonify({"success": True})


@app.after_request
def after_request(response):
    """
    Ensure all responses include proper CORS headers
    """
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    return response


@app.route("/")
def home():
    return "Flask + MongoDB backend running on Railway!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
