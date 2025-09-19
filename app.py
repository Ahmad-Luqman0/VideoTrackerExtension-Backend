from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from bson import ObjectId
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.test
users = db.users


# --- Helper: End a session (set endtime + duration) ---
def end_session(user_id, session_id, endtime=None):
    if not endtime:
        endtime = datetime.utcnow()

    user = users.find_one({"_id": user_id, "sessions._id": session_id}, {"sessions.$": 1})
    if not user or "sessions" not in user:
        return

    session = user["sessions"][0]
    starttime = session.get("starttime")
    duration = None
    if starttime:
        duration = (endtime - starttime).total_seconds()

    users.update_one(
        {"_id": user_id, "sessions._id": session_id},
        {"$set": {"sessions.$.endtime": endtime, "sessions.$.duration": duration}},
    )


# --- Helper: Ensure session is active, split if >3 min inactivity ---
def ensure_active_session(user_id, session_id):
    uid = ObjectId(user_id)
    oid = ObjectId(session_id)

    user = users.find_one({"_id": uid, "sessions._id": oid}, {"sessions.$": 1})
    if not user or "sessions" not in user:
        return None

    session = user["sessions"][0]
    last_activity = session.get("last_activity", session.get("starttime"))
    now = datetime.utcnow()

    if last_activity and now - last_activity > timedelta(minutes=3):
        # close old session
        end_session(uid, oid, last_activity)

        # start new session
        new_session = {
            "_id": ObjectId(),
            "starttime": now,
            "endtime": None,
            "duration": None,
            "last_activity": now,
            "videos": [],
            "inactivity": [],
        }
        users.update_one({"_id": uid}, {"$push": {"sessions": new_session}})
        return new_session["_id"]

    # otherwise update last_activity
    users.update_one(
        {"_id": uid, "sessions._id": oid},
        {"$set": {"sessions.$.last_activity": now}},
    )
    return oid


# --- LOGIN ---
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = users.find_one({"username": username, "password": password})
    if not user:
        return jsonify({"success": False}), 401

    # build a new session
    session = {
        "_id": ObjectId(),
        "starttime": datetime.utcnow(),
        "endtime": None,
        "duration": None,
        "last_activity": datetime.utcnow(),
        "videos": [],
        "inactivity": [],
    }

    users.update_one({"_id": user["_id"]}, {"$push": {"sessions": session}})

    return jsonify(
        {"success": True, "session_id": str(session["_id"]), "user_id": str(user["_id"])}
    )


# --- LOGOUT ---
@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    session_id = data.get("session_id")
    user_id = data.get("user_id")

    if not session_id or not user_id:
        return jsonify({"success": False, "error": "Missing user_id or session_id"}), 400

    try:
        uid = ObjectId(user_id)
        oid = ObjectId(session_id)
    except Exception:
        return jsonify({"success": False, "error": "Invalid IDs"}), 400

    end_session(uid, oid)

    return jsonify({"success": True})


# --- LOG VIDEO ---
@app.route("/log_video", methods=["POST"])
def log_video():
    data = request.json
    session_id = data.get("session_id")
    user_id = data.get("user_id")

    if not session_id or not user_id:
        return jsonify({"success": False, "error": "Missing user_id or session_id"}), 400

    try:
        oid = ensure_active_session(user_id, session_id)
        if not oid:
            return jsonify({"success": False, "error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    video_entry = {
        "videoId": data.get("videoId"),
        "duration": data.get("duration"),
        "watched": data.get("watched"),
        "status": data.get("status"),
        "keys": data.get("keys", []),
    }

    result = users.update_one(
        {"sessions._id": oid}, {"$push": {"sessions.$.videos": video_entry}}
    )

    if result.modified_count == 0:
        return jsonify({"success": False, "error": "Session not found"}), 404

    return jsonify({"success": True, "video": video_entry})


# --- LOG INACTIVITY ---
@app.route("/log_inactivity", methods=["POST"])
def log_inactivity():
    data = request.json
    session_id = data.get("session_id")
    user_id = data.get("user_id")

    if not session_id or not user_id:
        return jsonify({"success": False, "error": "Missing user_id or session_id"}), 400

    try:
        oid = ensure_active_session(user_id, session_id)
        if not oid:
            return jsonify({"success": False, "error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    inactivity_entry = {
        "starttime": data.get("starttime"),
        "endtime": data.get("endtime"),
        "duration": data.get("duration"),
        "type": data.get("type"),
    }

    result = users.update_one(
        {"sessions._id": oid}, {"$push": {"sessions.$.inactivity": inactivity_entry}}
    )

    if result.modified_count == 0:
        return jsonify({"success": False, "error": "Session not found"}), 404

    return jsonify({"success": True, "inactivity": inactivity_entry})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
