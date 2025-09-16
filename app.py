import os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Get Mongo URI from Railway environment variable
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.test
users = db.users


# --- LOGIN ---
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if users.find_one({"username": username, "password": password}):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})


# --- LOG FINALIZED VIDEO ---
@app.route("/log_video", methods=["POST"])
def log_video():
    data = request.json
    username = data.get("username")

    video_url = data.get("video_url")
    duration = data.get("duration")
    watched = data.get("watched")
    status = data.get("status")
    remarks = data.get("remarks")
    keys_pressed = data.get("keys_pressed", [])

    # Only log if Not Watched Before
    if remarks != "Not Watched Before":
        return jsonify({"success": False, "reason": "Already watched before"})

    user = users.find_one({"username": username})
    if not user:
        return jsonify({"success": False, "reason": "User not found"})

    serial = len(user.get("videos", [])) + 1

    video_entry = {
        "serial": serial,
        "video_url": video_url,
        "duration": duration,
        "watched": watched,
        "status": status,
        "remarks": remarks,
        "keys_pressed": keys_pressed,
        "timestamp": datetime.now().isoformat()
    }

    users.update_one({"username": username}, {"$push": {"videos": video_entry}})

    return jsonify({"success": True, "logged": video_entry})


# --- LOG INACTIVITY SESSION ---
@app.route("/log_inactivity", methods=["POST"])
def log_inactivity():
    data = request.json
    username = data.get("username")

    start_time = data.get("start_time")
    end_time = data.get("end_time")
    duration = data.get("duration")
    mode = data.get("mode")

    user = users.find_one({"username": username})
    if not user:
        return jsonify({"success": False, "reason": "User not found"})

    serial = len(user.get("inactivity", [])) + 1

    inactivity_entry = {
        "serial": serial,
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "mode": mode
    }

    users.update_one({"username": username}, {"$push": {"inactivity": inactivity_entry}})

    return jsonify({"success": True, "logged": inactivity_entry})


@app.route("/")
def home():
    return "✅ Flask + MongoDB backend running on Railway with video + inactivity logging!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
