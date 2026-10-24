"""RFC 4226/6238: HMAC, contador big-endian y truncamiento dinámico propios."""
import base64
import hashlib
import hmac
import re
import struct
import time


def decode_base32(secret: str) -> bytes:
    value = secret.strip().replace(" ", "").upper().rstrip("=")
    if not value or not re.fullmatch(r"[A-Z2-7]+", value):
        raise ValueError("Semilla Base32 inválida")
    return base64.b32decode(value + "=" * ((-len(value)) % 8))


def hotp(secret: str, counter: int, digits: int = 6) -> str:
    digest = hmac.new(decode_base32(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def totp(secret: str, timestamp: float | None = None, digits: int = 6) -> str:
    return hotp(secret, int(time.time() if timestamp is None else timestamp) // 30, digits)


def match_window(secret: str, code: str, timestamp: float) -> int | None:
    if not re.fullmatch(r"[0-9]{6}", code):
        return None
    counter = int(timestamp) // 30
    for delta in (0, -1, 1):
        if counter + delta >= 0 and hmac.compare_digest(hotp(secret, counter + delta), code):
            return delta
    return None
