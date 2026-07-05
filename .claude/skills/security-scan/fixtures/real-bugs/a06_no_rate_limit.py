"""A06 — Insecure Design (no rate limiting on auth)."""
from flask import Blueprint, request, jsonify

from .auth import check_credentials, issue_session

bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    username = request.form["username"]
    password = request.form["password"]
    if check_credentials(username, password):
        return jsonify({"token": issue_session(username)})
    return jsonify({"error": "invalid"}), 401