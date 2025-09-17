import os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Railway stores Mongo URI in env
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.test
users = db.users


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if users.find_one({"username": username, "password": password}):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})


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

    # Push video entry into the user document
    users.update_one(
        {"username": username},
        {"$push": {"videos": video_entry}}
    )

    return jsonify({"success": True})


@app.route("/")
def home():
    return "✅ Flask + MongoDB backend running on Railway!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
