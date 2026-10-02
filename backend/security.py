import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request
from sqlalchemy import select

from .models import Sesion, Usuario


COOKIE_NAME = "campusquest_session"
PASSWORD_ITERATIONS = 600_000


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2-sha256${PASSWORD_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2-sha256" or not 100_000 <= int(iterations) <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
