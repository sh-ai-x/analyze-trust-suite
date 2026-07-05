"""Ratio with an explicit zero-denominator guard."""


def safe_ratio(numerator, denominator):
    if denominator == 0:
        raise ValueError("denominator must be non-zero")
    return numerator / denominator
