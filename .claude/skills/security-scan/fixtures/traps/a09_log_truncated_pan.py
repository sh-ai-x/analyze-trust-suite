"""A09 trap — logs a PAN, but only the last 4 digits. Not full PAN, not PII-
grade leakage.
"""
import logging

log = logging.getLogger(__name__)


def charge(pan: str, amount_cents: int) -> None:
    log.info("charge card=****%s amount=%d", pan[-4:], amount_cents)