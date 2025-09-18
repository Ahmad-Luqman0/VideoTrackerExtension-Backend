import os
from datetime import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Railway provides Mongo URI in env variable
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.test
users = db.users


# ---------------------------
# Login (start new session)
# ---------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = users.find_one({"username": username, "password": password})
    if not user:
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    # determine next sessionId
    last_session_id = 0
    if "sessions" in user and len(user["sessions"]) > 0:
        last_session_id = user["sessions"][-1]["sessionId"]

    new_session = {
        "sessionId": last_session_id + 1,
        "startTime": datetime.utcnow().isoformat(),
        "endTime": None,
        "videos": []
    }

    # push new session
    users.update_one(
        {"username": username},
        {"$push": {"sessions": new_session}}
    )

    return jsonify({"success": True, "sessionId": new_session["sessionId"]})


# ---------------------------
# Log a video inside session
# ---------------------------
@app.route("/log_video", methods=["POST"])
def log_video():
    data = request.json
    username = data.get("username")
    video_entry = {
        "videoId": data.get("videoId"),
        "duration": data.get("duration"),
        "watched": data.get("watched"),
        "status": data.get("status"),
        "keys": data.get("keys", [])
    }

    if not username or not video_entry["videoId"]:
        return jsonify({"success": False, "error": "Missing username or videoId"}), 400

    # find last session
    user = users.find_one({"username": username})
    if not user or "sessions" not in user or len(user["sessions"]) == 0:
        return jsonify({"success": False, "error": "No active session"}), 400

    last_session_id = user["sessions"][-1]["sessionId"]

    # push video into last session
    users.update_one(
        {"username": username, "sessions.sessionId": last_session_id},
        {"$push": {"sessions.$.videos": video_entry}}
    )

    return jsonify({"success": True})


# ---------------------------
# Logout (end last session)
# ---------------------------
@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    username = data.get("username")

    user = users.find_one({"username": username})
    if not user or "sessions" not in user or len(user["sessions"]) == 0:
        return jsonify({"success": False, "error": "No active session"}), 400

    last_session_id = user["sessions"][-1]["sessionId"]

    # set endTime for the last session
    users.update_one(
        {"username": username, "sessions.sessionId": last_session_id},
        {"$set": {"sessions.$.endTime": datetime.utcnow().isoformat()}}
    )

    return jsonify({"success": True, "sessionId": last_session_id})


# ---------------------------
# Default route
# ---------------------------
@app.route("/")
def home():
    return "✅ Flask + MongoDB backend running with session tracking!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
