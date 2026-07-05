"""A04 trap — MD5 used for a cache key, NOT a security context.

MD5 is fine for ETags / dedup hashes / content fingerprints. Only flag MD5 when
it's used for passwords, signatures, or any security purpose.
"""
import hashlib


def etag_for(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()