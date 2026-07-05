"""A10 — Mishandling of Exceptional Conditions (bare-except + fail-open transfer)."""
from .ledger import debit, credit


def transfer(src: str, dst: str, amount: int) -> bool:
    try:
        debit(src, amount)
        credit(dst, amount)
        return True
    except:  # noqa: E722 — bare-except on purpose, see bug below
        # If anything goes wrong we tell the caller "no" — but we also DROPPED
        # the half-finished debit. Fail-open: the ledger can be inconsistent.
        return False