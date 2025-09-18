# app.py
import os
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)
# allow CORS for extension + testing (adjust origins in production)
CORS(app, resources={r"/*": {"origins": "*"}})

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise Exception("❌ MONGO_URI is not set in Railway environment variables")

client = MongoClient(MONGO_URI)
db = client.test
users = db.users


def now_iso():
    return datetime.now(timezone.utc).isoformat()


@app.route("/", methods=["GET"])
def home():
    return "✅ Flask + MongoDB backend running with session support!"


@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "Missing username/password"}), 400

    user = users.find_one({"username": username, "password": password})
    if not user:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

    # create session object
    session_id = str(uuid.uuid4())
    session_entry = {
        "sessionId": session_id,
        "startTime": now_iso(),
        "endTime": None,
        "duration": None,
        "videos": [],
        "inactivity": []
    }

    users.update_one({"username": username}, {"$push": {"sessions": session_entry}})
    app.logger.info(f"[login] user={username} session={session_id}")
    return jsonify({"success": True, "sessionId": session_id})


@app.route("/logout", methods=["POST"])
def logout():
    data = request.json or {}
    username = data.get("username")
    session_id = data.get("sessionId")

    if not username or not session_id:
        return jsonify({"success": False, "error": "Missing username/sessionId"}), 400

    # find the session
    user = users.find_one({"username": username, "sessions.sessionId": session_id})
    if not user:
        return jsonify({"success": False, "error": "Invalid session"}), 403

    # compute duration
    sessions = user.get("sessions", [])
    target = next((s for s in sessions if s["sessionId"] == session_id), None)
    if not target or not target.get("startTime"):
        return jsonify({"success": False, "error": "Session not found or missing startTime"}), 404

    start = datetime.fromisoformat(target["startTime"])
    end = datetime.now(timezone.utc)
    duration_delta = end - start
    duration_seconds = int(duration_delta.total_seconds())
    duration_str = str(duration_delta)

    users.update_one(
        {"username": username, "sessions.sessionId": session_id},
        {"$set": {
            "sessions.$.endTime": end.isoformat(),
            "sessions.$.duration": duration_str,
            # optionally keep a numeric seconds field:
            "sessions.$.durationSeconds": duration_seconds
        }}
    )

    app.logger.info(f"[logout] user={username} session={session_id} duration_s={duration_seconds}")
    return jsonify({"success": True, "message": "Session closed", "duration": duration_str})


@app.route("/log_video", methods=["POST"])
def log_video():
    data = request.json or {}
    username = data.get("username")
    session_id = data.get("sessionId")
    video_id = data.get("videoId")

    if not username or not session_id or not video_id:
        return jsonify({"success": False, "error": "Missing username/sessionId/videoId"}), 400

    # validate session exists
    user = users.find_one({"username": username, "sessions.sessionId": session_id})
    if not user:
        return jsonify({"success": False, "error": "Invalid session"}), 403

    video_entry = {
        "videoId": video_id,
        "duration": data.get("duration"),
        "watched": data.get("watched"),
        "status": data.get("status"),
        "keys": data.get("keys", []),
        "loggedAt": now_iso()
    }

    # push into the matching session's videos array
    result = users.update_one(
        {"username": username, "sessions.sessionId": session_id},
        {"$push": {"sessions.$.videos": video_entry}}
    )

    if result.modified_count == 0:
        return jsonify({"success": False, "error": "Failed to push video"}), 500

    app.logger.info(f"[log_video] user={username} session={session_id} video={video_id}")
    return jsonify({"success": True, "message": "Video logged"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
