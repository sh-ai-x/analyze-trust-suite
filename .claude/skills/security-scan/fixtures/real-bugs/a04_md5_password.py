"""A04 — Cryptographic Failures.

MD5 used to hash passwords; non-constant-time compare against stored hash.
"""
import hashlib


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(password: str, stored: str) -> bool:
    # `==` on hashes is a timing oracle.
    return hash_password(password) == stored


def authenticate(username: str, password: str) -> bool:
    from .db import get_user
    user = get_user(username)
    if user is None:
        return False
    return verify_password(password, user.password_hash)