"""A10 — Fail-open on validation: when the validator itself errors, the input
is accepted anyway."""
from .validator import validate_age


def register(name: str, age: str) -> bool:
    try:
        if not validate_age(age):
            return False
    except Exception:
        pass  # validator crashed → proceed as if it passed
    save_user(name, age)
    return True