import os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Get Mongo URI from environment (Railway will store it)
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


@app.route("/")
def home():
    return "✅ Flask + MongoDB backend running on Railway!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
