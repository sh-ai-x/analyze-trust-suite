"""A08 trap — subprocess call WITHOUT shell=True and WITH a list of args.
No injection possible regardless of the user input.
"""
import subprocess
from flask import request


def convert(filename: str) -> bytes:
    completed = subprocess.run(
        ["/usr/bin/convert", f"/tmp/in/{filename}", f"/tmp/out/{filename}.png"],
        check=True,
        capture_output=True,
        timeout=10,
    )
    return completed.stdout