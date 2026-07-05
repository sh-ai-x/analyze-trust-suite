"""clean — well-formed endpoint. MUST return Approve / zero findings."""
import hashlib
import hmac
import logging
import secrets

from flask import Blueprint, jsonify, request

from .auth import require_user, issue_session
from .db import get_conn
from .models import Order

bp = Blueprint("orders", __name__)
log = logging.getLogger(__name__)


@bp.get("/orders/<int:order_id>")
@require_user
def get_order(order_id: int):
    user_id = request.user["id"]
    conn = get_conn()
    row = conn.execute(
        "SELECT id, total_cents, status FROM orders WHERE id = ? AND user_id = ?",
        (order_id, user_id),
    ).fetchone()
    if row is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(dict(row))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + ":" + dk.hex()


def verify_password(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split(":")
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), 200_000
    )
    return hmac.compare_digest(candidate, bytes.fromhex(dk_hex))


@bp.post("/login")
def login():
    username = request.form["username"]
    password = request.form["password"]
    user = _lookup_user(username)
    if user is None or not verify_password(password, user["pw_hash"]):
        # log with user id only, no password / no PII
        log.info("login_failed user=%s", username)
        return jsonify({"error": "invalid"}), 401
    return jsonify({"token": issue_session(user["id"])})


def _lookup_user(_username: str):  # stub
    return None


def _move(_src: str, _dst: str, _amount: int) -> None:
    return None