from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.cli import seed_catalog
from backend.config import Settings
from backend.models import Usuario
from backend.security import hash_password


PASSWORD = "Test_password_123"
HASH = hash_password(PASSWORD)


@pytest.fixture
def api(tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("<html>Campus Quest dashboard</html>")
    (frontend / "assets").mkdir()
    (frontend / "assets/app.js").write_text("console.log('Campus Quest')")
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", allowed_origins=("http://localhost:5173",), cookie_secure=False, frontend_dist_dir=frontend)
    app = create_app(settings)
    with TestClient(app) as client:
        users = {}
        with app.state.database.sessions.begin() as db:
            seed_catalog(db)
            for key, role in (("admin", "admin"), ("student", "estudiante"), ("other", "estudiante"), ("tutor", "tutor")):
                user = Usuario(nombres=key.capitalize(), correoInstitucional=f"{key}@live.uleam.edu.ec", carrera="Software", contrasenaHash=HASH, rol=role)
                db.add(user)
                db.flush()
                users[key] = user.id
        yield SimpleNamespace(client=client, app=app, users=users, settings=settings)


def login(api, key="admin", clear_cookie=True):
    response = api.client.post("/api/v1/auth/login", json={"correo": f"{key}@live.uleam.edu.ec", "contrasena": PASSWORD}, headers={"Origin": "http://testserver"})
    assert response.status_code == 200, response.text
    token = response.json()["accessToken"]
    if clear_cookie:
        api.client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}
