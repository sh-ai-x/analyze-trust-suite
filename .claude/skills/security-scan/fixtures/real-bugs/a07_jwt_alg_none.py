"""A07 — Authentication Failures (JWT alg=none)."""
import jwt
from flask import request, jsonify


def require_user(handler):
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        # alg=none → anyone can forge a token by setting alg=none in the header.
        payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["none"])
        request.user = payload["sub"]
        return handler(*args, **kwargs)
    return wrapper