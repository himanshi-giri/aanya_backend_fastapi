# from flask import Blueprint, request, jsonify
# from flask_jwt_extended import jwt_required
# from models import create_user, find_user
# from auth import authenticate_user

# auth_bp = Blueprint("auth", __name__)

# @auth_bp.route("/api/auth/login", methods=["POST"])
# def login():
#     data = request.json
#     email = data.get("email")
#     password = data.get("password")

#     token = authenticate_user(email, password)
#     if token:
#         return jsonify({"message": "Login successful", "token": token}), 200
#     return jsonify({"error": "Invalid credentials"}), 401

# @auth_bp.route("/api/auth/register", methods=["POST"])
# def register():
#     data = request.json
#     email = data.get("email")
#     password = data.get("password")

#     if find_user(email):
#         return jsonify({"error": "User already exists"}), 400

#     create_user(email, password)
#     return jsonify({"message": "User registered successfully"}), 201
