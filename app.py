import os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- MongoDB Connection ---
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set in Railway!")

client = MongoClient(MONGO_URI)
db = client.test   # default DB
users = db.users   # users collection


# --- Routes ---

@app.route("/")
def home():
    return "Flask + MongoDB backend running on Railway!"


@app.route("/login", methods=["POST"])
def login():
    """Simple username/password login."""
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "Missing username or password"}), 400

    user = users.find_one({"username": username, "password": password})
    if user:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})


@app.route("/log_video", methods=["POST"])
def log_video():
    """Log finalized video data for a given user."""
    data = request.json or {}
    username = data.get("username")
    video_entry = {
        "videoId": data.get("videoId"),
        "duration": data.get("duration"),
        "watched": data.get("watched"),
        "status": data.get("status"),
        "keys": data.get("keys", [])
    }

    # Validate required fields
    if not username or not video_entry["videoId"]:
        return jsonify({"success": False, "error": "Missing username or videoId"}), 400

    # Ensure user exists
    user = users.find_one({"username": username})
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    # Push video entry into the user's videos array
    users.update_one(
        {"username": username},
        {"$push": {"videos": video_entry}}
    )

    return jsonify({"success": True, "message": "Video logged"})


# --- Run Locally ---
if __name__ == "__main__":
    # Railway sets PORT env variable automatically
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
