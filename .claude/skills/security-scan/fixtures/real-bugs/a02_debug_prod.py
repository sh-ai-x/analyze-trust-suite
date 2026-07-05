"""A02 — Security Misconfiguration.

DEBUG=True in production + raw exception returned in HTTP response.
"""
DEBUG = True

from flask import Flask, jsonify

app = Flask(__name__)


@app.errorhandler(Exception)
def handle(e):
    # Returns the full traceback to the client.
    import traceback
    return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.get("/health")
def health():
    return {"ok": True}