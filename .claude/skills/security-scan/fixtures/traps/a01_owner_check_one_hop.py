"""A01 trap — the `get_order` handler reads by id with no visible check, but
the `require_owner` decorator on the route enforces ownership one frame up.
"""
from flask import Blueprint
from flask_login import current_user

from .models import Order, db
from .decorators import require_owner

bp = Blueprint("orders", __name__)


@bp.get("/orders/<int:order_id>")
@require_owner(Order)
def get_order(order_id: int):
    order = db.session.get(Order, order_id)
    return {"order": order.to_dict()}