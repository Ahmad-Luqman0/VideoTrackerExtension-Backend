from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import os
from bson import ObjectId
from flask_cors import CORS
import re
import secrets

app = Flask(__name__)
CORS(app)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.test
users = db.users


def validate_username(username):
    """
    Validate username:
    - 8-15 characters
    - At least one number
    - At least one special character (only . - _ allowed)
    - Only letters, numbers, and . - _ allowed
    """
    if not username or len(username) < 8 or len(username) > 15:
        return False, "Username must be 8-15 characters long"

    if not re.search(r"\d", username):
        return False, "Username must contain at least one number"

    if not re.search(r"[.\-_]", username):
        return False, "Username must contain at least one special character (. - _)"

    if not re.match(r"^[a-zA-Z0-9.\-_]+$", username):
        return False, "Username can only contain letters, numbers, and . - _"

    return True, "Valid username"


def validate_password(password):
    """
    Validate password:
    - At least 8 characters
    - At least one uppercase letter
    - At least one number
    - At least one special character
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/\';`~]', password):
        return False, "Password must contain at least one special character"

    return True, "Valid password"


def generate_session_id():
    """Generate a secure random session ID"""
    return secrets.token_urlsafe(32)


@app.route("/", methods=["GET"])
def home():
    return "BackEnd Running  :)"


# --- REGISTER (create new user with duplicate prevention) ---
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    # Validate input
    if not username or not password:
        return (
            jsonify({"success": False, "error": "Username and password are required"}),
            400,
        )

    # Validate username format
    is_valid, error_msg = validate_username(username)
    if not is_valid:
        return jsonify({"success": False, "error": error_msg}), 400

    # Validate password format
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return jsonify({"success": False, "error": error_msg}), 400

    # Check for duplicate username
    existing_user = users.find_one({"username": username})
    if existing_user:
        return jsonify({"success": False, "error": "Username already exists"}), 409

    # Create new user
    new_user = {"username": username, "password": password, "sessions": []}

    try:
        result = users.insert_one(new_user)
        return jsonify({"success": True, "user_id": str(result.inserted_id)})
    except Exception as e:
        return jsonify({"success": False, "error": "Failed to create user"}), 500


# --- LOGIN (create new session for the user) ---
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = users.find_one({"username": username, "password": password})
    if not user:
        return jsonify({"success": False}), 401

    # Build a new session with secure random session ID
    session_id = generate_session_id()
    session = {
        "_id": session_id,  # Use secure random string instead of ObjectId
        "starttime": datetime.utcnow(),
        "endtime": None,
        "duration": None,
        "videos": [],
        "inactivity": [],
    }

    users.update_one({"_id": user["_id"]}, {"$push": {"sessions": session}})

    return jsonify({"success": True, "session_id": session_id})


# --- LOGOUT (set endtime + duration on last session) ---
@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"success": False, "error": "Missing session_id"}), 400

    # Session ID is now a string, no need to convert to ObjectId
    # get session starttime first
    user = users.find_one({"sessions._id": session_id}, {"sessions.$": 1})
    if not user or "sessions" not in user or len(user["sessions"]) == 0:
        return jsonify({"success": False, "error": "Session not found"}), 404

    session = user["sessions"][0]
    starttime = session.get("starttime")
    endtime = datetime.utcnow()
    duration = None
    if starttime:
        duration = (endtime - starttime).total_seconds()

    users.update_one(
        {"sessions._id": session_id},
        {"$set": {"sessions.$.endtime": endtime, "sessions.$.duration": duration}},
    )

    return jsonify(
        {"success": True, "endtime": endtime.isoformat(), "duration": duration}
    )


# --- LOG VIDEO (simplified: store duration, watched, status, soundMuted) ---
@app.route("/log_video", methods=["POST"])
def log_video():
    data = request.json
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"success": False, "error": "Missing session_id"}), 400

    # Session ID is now a string, no need to convert to ObjectId

    # Get sound muted state as simple boolean (yes/no)
    sound_muted = data.get("soundMuted", False)  # Default to False (not muted)
    # Convert to "yes" if muted, "no" if not muted
    sound_muted_status = "yes" if sound_muted else "no"

    video_id = data.get("videoId")
    duration = float(data.get("duration", 0))
    watched = int(data.get("watched", 0))
    status = data.get("status", "Not Watched")

    # Try to update existing video in the session
    result = users.update_one(
        {"sessions._id": session_id, "sessions.videos.videoId": video_id},
        {
            "$set": {
                "sessions.$.videos.$[video].duration": duration,
                "sessions.$.videos.$[video].watched": watched,
                "sessions.$.videos.$[video].status": status,
                "sessions.$.videos.$[video].soundMuted": sound_muted_status,
            }
        },
        array_filters=[{"video.videoId": video_id}],
    )

    # If the video was not found in the session, push a new one
    if result.matched_count == 0:
        video_entry = {
            "videoId": video_id,
            "duration": duration,
            "watched": watched,
            "status": status,
            "soundMuted": sound_muted_status,
        }
        users.update_one(
            {"sessions._id": session_id}, {"$push": {"sessions.$.videos": video_entry}}
        )
        return jsonify({"success": True, "video": video_entry})

    # Return updated video
    updated_video = {
        "videoId": video_id,
        "duration": duration,
        "watched": watched,
        "status": status,
        "soundMuted": sound_muted_status,
    }
    return jsonify({"success": True, "video": updated_video})


# --- LOG INACTIVITY (push inactivity events into session) ---
@app.route("/log_inactivity", methods=["POST"])
def log_inactivity():
    data = request.json
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"success": False, "error": "Missing session_id"}), 400

    # Session ID is now a string, no need to convert to ObjectId

    inactivity_entry = {
        "starttime": data.get("starttime"),
        "endtime": data.get("endtime"),
        "duration": data.get("duration"),
        "type": data.get("type"),
    }

    # Push inactivity log
    result = users.update_one(
        {"sessions._id": session_id},
        {"$push": {"sessions.$.inactivity": inactivity_entry}},
    )

    if result.modified_count == 0:
        return jsonify({"success": False, "error": "Session not found"}), 404

    # --- Check inactivity duration ---
    try:
        inactivity_duration = float(inactivity_entry.get("duration", 0))
    except Exception:
        inactivity_duration = 0

    if inactivity_duration > 180:
        # End current session
        user = users.find_one({"sessions._id": session_id}, {"sessions.$": 1, "_id": 1})
        if user and "sessions" in user and len(user["sessions"]) > 0:
            session = user["sessions"][0]
            starttime = session.get("starttime")
            endtime = datetime.utcnow()
            duration = None
            if starttime:
                duration = (endtime - starttime).total_seconds()

            users.update_one(
                {"sessions._id": session_id},
                {
                    "$set": {
                        "sessions.$.endtime": endtime,
                        "sessions.$.duration": duration,
                    }
                },
            )

            # Create a new session (start after inactivity ends) with secure random ID
            new_session_id = generate_session_id()
            new_session = {
                "_id": new_session_id,
                "starttime": endtime,
                "endtime": None,
                "duration": None,
                "videos": [],
                "inactivity": [],
            }

            users.update_one({"_id": user["_id"]}, {"$push": {"sessions": new_session}})

            return jsonify(
                {
                    "success": True,
                    "inactivity": inactivity_entry,
                    "action": "session_split",
                    "new_session_id": new_session_id,
                }
            )

    return jsonify({"success": True, "inactivity": inactivity_entry})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
