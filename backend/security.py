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


def request_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(401, "Sesión inválida.", headers={"WWW-Authenticate": "Bearer"})
        return token.strip()
    return request.cookies.get(COOKIE_NAME)


@dataclass
class AuthContext:
    usuario: Usuario
    token_hash: str


def current_auth(request: Request) -> AuthContext:
    token = request_token(request)
    if not token:
        raise HTTPException(401, "Inicia sesión para continuar.", headers={"WWW-Authenticate": "Bearer"})
    hashed = token_hash(token)
    with request.app.state.database.sessions() as db:
        session = db.scalar(select(Sesion).where(Sesion.tokenHash == hashed, Sesion.expiraEn > now_ms()))
        user = db.get(Usuario, session.usuarioId) if session else None
        if user is None:
            raise HTTPException(401, "La sesión expiró o fue revocada.", headers={"WWW-Authenticate": "Bearer"})
        return AuthContext(user, hashed)


def require_admin(request: Request) -> AuthContext:
    auth = current_auth(request)
    if auth.usuario.rol != "admin":
        raise HTTPException(403, "Esta operación requiere una cuenta administradora.")
    return auth


def require_owner(auth: AuthContext, usuario_id: int):
    if auth.usuario.rol == "admin":
        return
    if auth.usuario.rol not in {"estudiante", "visitante"} or auth.usuario.id != usuario_id:
        raise HTTPException(403, "No puedes consultar ni modificar este usuario.")
