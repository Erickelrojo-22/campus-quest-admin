import os
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    if raw not in {"true", "false", "1", "0"}:
        raise ValueError(f"{name} debe ser true o false.")
    return raw in {"true", "1"}


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'backend/data/campus_quest.db'}"))
    allowed_origins: tuple[str, ...] = field(default_factory=lambda: tuple(origin.strip().rstrip("/") for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()))
    cookie_secure: bool = field(default_factory=lambda: env_bool("COOKIE_SECURE"))
    session_ttl_hours: int = field(default_factory=lambda: int(os.getenv("SESSION_TTL_HOURS", "24")))
    frontend_dist_dir: Path = field(default_factory=lambda: Path(os.getenv("FRONTEND_DIST_DIR", str(ROOT / "frontend/dist"))))
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development").lower())

    def __post_init__(self):
        if self.app_env == "production" and not self.cookie_secure:
            raise ValueError("APP_ENV=production requiere COOKIE_SECURE=true y HTTPS.")
        if not 1 <= self.session_ttl_hours <= 720:
            raise ValueError("SESSION_TTL_HOURS debe estar entre 1 y 720.")
        if "*" in self.allowed_origins:
            raise ValueError("ALLOWED_ORIGINS debe contener orígenes explícitos.")
