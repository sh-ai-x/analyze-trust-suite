"""A01 — Broken Access Control (IDOR).

Endpoint reads an order by id from the URL with no ownership check.
Any authenticated user can fetch any other user's order.
"""
from flask import Blueprint, request, jsonify
from flask_login import current_user

from .models import Order, db

bp = Blueprint("orders", __name__)


@bp.get("/orders/<int:order_id>")
def get_order(order_id: int):
    order = db.session.get(Order, order_id)
    return jsonify(order.to_dict())


@bp.delete("/orders/<int:order_id>")
def delete_order(order_id: int):
    order = db.session.get(Order, order_id)
    db.session.delete(order)
    db.session.commit()
    return ("", 204)