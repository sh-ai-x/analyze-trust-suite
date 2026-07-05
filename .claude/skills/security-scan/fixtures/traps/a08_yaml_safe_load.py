"""A08 trap — uses yaml.safe_load, which does NOT execute arbitrary Python
objects. yaml.load without a SafeLoader would; this one is safe.
"""
import yaml


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)