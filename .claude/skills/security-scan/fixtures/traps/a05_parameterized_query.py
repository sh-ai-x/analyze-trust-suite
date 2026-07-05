"""A05 trap — looks like string interpolation in SQL, but is parameterized.

The `?` placeholder binds the value as a parameter — no injection even though
`name` is user-controlled.
"""
from .db import get_conn


def search_users(name: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, email FROM users WHERE name = ? ORDER BY id",
        (name,),
    ).fetchall()
    return [dict(r) for r in rows]