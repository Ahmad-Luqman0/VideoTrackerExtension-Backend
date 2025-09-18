import os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.test
users = db.users  # still holds users
sessions = db.sessions  # new collection for sessions

# --- LOGIN (Start session) ---
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if users.find_one({"username": username, "password": password}):
        # create new session doc
        session = {
            "username": username,
            "password": password,  # ⚠️ optional, usually shouldn't store plaintext
            "starttime": datetime.utcnow(),
            "endtime": None,
            "videos": []
        }
        session_id = sessions.insert_one(session).inserted_id
        return jsonify({"success": True, "session_id": str(session_id)})
    else:
        return jsonify({"success": False})

# --- LOGOUT (End session) ---
@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    session_id = data.get("session_id")

    if session_id:
        from bson import ObjectId
        sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"endtime": datetime.utcnow()}}
        )
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Missing session_id"})

# --- LOG VIDEO (append into session.videos[]) ---
@app.route("/log_video", methods=["POST"])
def log_video():
    data = request.json
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"success": False, "error": "Missing session_id"})

    from bson import ObjectId
    video_entry = {
        "videoId": data.get("videoId"),
        "duration": data.get("duration"),
        "watched": data.get("watched"),
        "status": data.get("status"),
        "keys": data.get("keys", [])
    }

    sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$push": {"videos": video_entry}}
    )
    return jsonify({"success": True, "video": video_entry})

@app.route("/")
def home():
    return "✅ Flask + MongoDB backend running on Railway!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
