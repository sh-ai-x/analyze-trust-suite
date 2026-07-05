"""A08 — Software or Data Integrity Failures (unsafe deserialization)."""
import pickle
from flask import Blueprint, request

bp = Blueprint("restore", __name__)


@bp.post("/restore")
def restore_session():
    # Reading the raw bytes of the request body and unpickling → RCE.
    blob = request.get_data()
    state = pickle.loads(blob)
    return {"restored": list(state.keys())}