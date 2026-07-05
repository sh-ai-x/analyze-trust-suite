"""A05 — Injection (command)."""
import subprocess
from flask import Blueprint, request

bp = Blueprint("tools", __name__)


@bp.post("/tools/convert")
def convert():
    filename = request.form["filename"]
    # shell=True + f-string → classic command injection.
    subprocess.call(f"convert /tmp/in/{filename} /tmp/out/{filename}.png", shell=True)
    return {"ok": True}