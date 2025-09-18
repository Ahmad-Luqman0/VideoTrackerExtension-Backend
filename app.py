import os
import uuid
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Railway provides MONGO_URI in environment variables
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise Exception("❌ MONGO_URI is not set in Railway environment variables")

client = MongoClient(MONGO_URI)
db = client.test
users = db.users

@app.route("/", methods=["GET"])
def home():
    return "✅ Flask + MongoDB backend running with session support!"


# -------------------
# LOGIN
# -------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = users.find_one({"username": username, "password": password})
    if user:
        # ✅ Generate new sessionId
        session_id = str(uuid.uuid4())

        # Save sessionId to user
        users.update_one(
            {"username": username},
            {"$set": {"sessionId": session_id}}
        )

        return jsonify({"success": True, "sessionId": session_id})
    else:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401


# -------------------
# LOGOUT
# -------------------
@app.route("/logout", methods=["POST"])
def logout():
    data = request.json
    username = data.get("username")
    session_id = data.get("sessionId")

    if not username or not session_id:
        return jsonify({"success": False, "error": "Missing username/sessionId"}), 400

    user = users.find_one({"username": username, "sessionId": session_id})
    if not user:
        return jsonify({"success": False, "error": "Invalid session"}), 403

    # Remove sessionId on logout
    users.update_one({"username": username}, {"$unset": {"sessionId": ""}})
    return jsonify({"success": True, "message": "Logged out"})


# -------------------
# LOG VIDEO
# -------------------
@app.route("/log_video", methods=["POST"])
def log_video():
    data = request.json
    username = data.get("username")
    session_id = data.get("sessionId")
    video_id = data.get("videoId")

    if not username or not session_id or not video_id:
        return jsonify({"success": False, "error": "Missing username/sessionId/videoId"}), 400

    # Validate session
    user = users.find_one({"username": username, "sessionId": session_id})
    if not user:
        return jsonify({"success": False, "error": "Invalid session"}), 403

    video_entry = {
        "videoId": video_id,
        "duration": data.get("duration"),
        "watched": data.get("watched"),
        "status": data.get("status"),
        "keys": data.get("keys", []),
    }

    # Push video entry into user's "videos" array
    users.update_one(
        {"username": username},
        {"$push": {"videos": video_entry}}
    )

    return jsonify({"success": True, "message": "Video logged"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
