import os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# MongoDB URI from environment
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.test
users = db.users  # main collection for users

# --- Helper Functions ---
def get_user(username):
    return users.find_one({"username": username})

def ensure_user_collections(username):
    """Ensure videos and inactivity lists exist for a user."""
    user = get_user(username)
    if user is None:
        return None
    if "videos" not in user:
        users.update_one({"username": username}, {"$set": {"videos": []}})
    if "inactivity" not in user:
        users.update_one({"username": username}, {"$set": {"inactivity": []}})
    return get_user(username)

# --- Routes ---

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    user = users.find_one({"username": username, "password": password})
    if user:
        # ensure collections exist
        ensure_user_collections(username)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/log", methods=["POST"])
def log_data():
    data = request.json
    username = data.get("username")
    if not username or not get_user(username):
        return jsonify({"success": False, "error": "Invalid user"})

    user = ensure_user_collections(username)

    log_type = data.get("type")
    if log_type == "video":
        # Video log
        video_log = {
            "id": data.get("id"),
            "src": data.get("src"),
            "duration": data.get("duration"),
            "watched": data.get("watched"),
            "status": data.get("status"),
            "keys": data.get("keys", []),
            "remark": data.get("remark")
        }
        users.update_one({"username": username}, {"$push": {"videos": video_log}})
        return jsonify({"success": True, "msg": "Video logged"})
    elif log_type == "inactivity":
        # Inactivity log
        inactivity_log = {
            "start": data["session"]["start"],
            "end": data["session"]["end"],
            "duration": data["session"]["duration"],
            "mode": data["session"]["mode"]
        }
        users.update_one({"username": username}, {"$push": {"inactivity": inactivity_log}})
        return jsonify({"success": True, "msg": "Inactivity logged"})
    else:
        return jsonify({"success": False, "error": "Unknown log type"})

@app.route("/")
def home():
    return "Backend Running"

# --- Run Server ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
