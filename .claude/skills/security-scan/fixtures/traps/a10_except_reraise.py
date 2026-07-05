"""A10 trap — broad except, but it logs AND re-raises. Not a swallowed error.
The bare `except:` family of bugs is "I dropped the error" — this one keeps it.
"""
import logging

log = logging.getLogger(__name__)


def transfer(src: str, dst: str, amount: int) -> None:
    try:
        _move(src, dst, amount)
    except Exception as e:
        log.exception("transfer failed src=%s dst=%s amount=%d", src, dst, amount)
        raise