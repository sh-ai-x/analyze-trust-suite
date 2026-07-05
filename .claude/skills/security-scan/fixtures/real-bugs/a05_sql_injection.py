"""A05 — Injection (SQL)."""
from flask import Blueprint, request, jsonify

from .db import get_conn

bp = Blueprint("users", __name__)


@bp.get("/users/search")
def search():
    name = request.args["name"]
    conn = get_conn()
    # f-string interpolation directly into the SQL statement.
    sql = f"SELECT id, email FROM users WHERE name = '{name}' ORDER BY id"
    rows = conn.execute(sql).fetchall()
    return jsonify([dict(r) for r in rows])