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
users = db.users
user_data = db.user_data

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if users.find_one({"username": username, "password": password}):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})

@app.route("/save_video", methods=["POST"])
def save_video():
    data = request.json
    username = data.get("username")

    last_entry = user_data.find_one({"username": username}, sort=[("serial", -1)])
    next_serial = (last_entry["serial"] + 1) if last_entry else 1

    entry = {
        "serial": next_serial,
        "username": username,
        "videoId": data.get("videoId"),
        "duration": data.get("duration"),
        "watched": data.get("watched"),
        "status": data.get("status"),
        "timestamp": datetime.utcnow()
    }

    user_data.insert_one(entry)
    return jsonify({"success": True, "entry": entry})

@app.route("/get_videos/<username>", methods=["GET"])
def get_videos(username):
    records = list(user_data.find({"username": username}, {"_id": 0}))
    return jsonify(records)

@app.route("/")
def home():
    return "✅ Flask + MongoDB backend running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
