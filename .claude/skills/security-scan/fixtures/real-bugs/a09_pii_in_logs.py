"""A09 — Security Logging and Alerting Failures (PII in logs)."""
import logging

log = logging.getLogger(__name__)


def process_payment(user_id: str, password: str, card_number: str, amount_cents: int) -> None:
    log.info(
        "payment user=%s password=%s card=%s amount=%d",
        user_id, password, card_number, amount_cents,
    )
    # ... actually charge the card ...