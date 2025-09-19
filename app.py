from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from bson import ObjectId
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client.test
users = db.users  # only this collection

# --- LOGIN (create new session for the user) ---
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = users.find_one({"username": username, "password": password})
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    # Close any unfinished session
    if user.get("sessions"):
        last_session = user["sessions"][-1]
        if last_session.get("endtime") is None:
            users.update_one(
                {"_id": user["_id"], "sessions._id": last_session["_id"]},
                {"$set": {
                    "sessions.$.endtime": datetime.utcnow(),
                    "sessions.$.duration": (
                        datetime.utcnow() - last_session["starttime"]
                    ).total_seconds()
                }}
            )

    # Create a new session
    session = {
        "_id": ObjectId(),
        "starttime": datetime.utcnow(),
        "endtime": None,
        "duration": None,
        "videos": []
    }

    users.update_one(
        {"_id": user["_id"]},
        {"$push": {"sessions": session}}
    )

    return jsonify({"message": "Login successful", "session_id": str(session["_id"])})


# --- ACTIVITY (mouse/keyboard active) ---
@app.route("/activity", methods=["POST"])
def activity():
    data = request.json
    username = data.get("username")
    activity_time = datetime.utcnow()

    user = users.find_one({"username": username})
    if not user or not user.get("sessions"):
        return jsonify({"error": "User not logged in"}), 400

    last_session = user["sessions"][-1]
    last_end = last_session.get("endtime")

    if last_end:
        if activity_time - last_end > timedelta(minutes=3):            
            if last_session.get("duration") is None:
                duration = (last_end - last_session["starttime"]).total_seconds()
                users.update_one(
                    {"_id": user["_id"], "sessions._id": last_session["_id"]},
                    {"$set": {"sessions.$.duration": duration}}
                )

            # start a new session
            new_session = {
                "_id": ObjectId(),
                "starttime": activity_time,
                "endtime": None,
                "duration": None,
                "videos": []
            }
            users.update_one(
                {"_id": user["_id"]},
                {"$push": {"sessions": new_session}}
            )
            return jsonify({"message": "New session started due to 2h inactivity"})

    # else continue in current session (do nothing special)
    return jsonify({"message": "Activity recorded"})


# --- INACTIVITY (blur or idle stop) ---
@app.route("/inactivity", methods=["POST"])
def inactivity():
    data = request.json
    username = data.get("username")
    inactivity_time = datetime.utcnow()

    user = users.find_one({"username": username})
    if not user or not user.get("sessions"):
        return jsonify({"error": "User not logged in"}), 400

    last_session = user["sessions"][-1]
    if last_session.get("endtime") is None:
        duration = (inactivity_time - last_session["starttime"]).total_seconds()
        users.update_one(
            {"_id": user["_id"], "sessions._id": last_session["_id"]},
            {"$set": {
                "sessions.$.endtime": inactivity_time,
                "sessions.$.duration": duration
            }}
        )

    return jsonify({"message": "Session marked inactive"})


if __name__ == "__main__":
    app.run(debug=True)
