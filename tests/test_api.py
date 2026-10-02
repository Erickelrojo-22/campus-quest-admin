from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

from backend.cli import create_admin, seed_demo
from backend.config import Settings
from backend.models import ProgresoMision, Sesion, Usuario
from backend.security import COOKIE_NAME, now_ms, token_hash
from conftest import PASSWORD, login


def mission_body(api, headers, mission_id=1):
    missions = api.client.get("/api/v1/misiones?incluirArchivadas=true", headers=headers).json()
    return {key: value for key, value in next(m for m in missions if m["id"] == mission_id).items() if key != "id"}


def point_body(api, headers, point_id=1):
    points = api.client.get("/api/v1/puntos", headers=headers).json()
    return {key: value for key, value in next(p for p in points if p["id"] == point_id).items() if key != "id"}


def test_health_spa_and_unknown_api_routes(api):
    assert api.client.get("/api/v1/health").json() == {"status": "ok"}
    assert "Campus Quest dashboard" in api.client.get("/usuarios/42").text
    assert api.client.get("/assets/app.js").status_code == 200
    for path in ("/assets/missing.js", "/missing.png", "/docs/missing", "/api/v1/missing", "/api"):
        assert api.client.get(path).status_code == 404
    assert api.client.post("/api/v1/missing").status_code == 404
    assert api.client.get("/openapi.json").status_code == 200


def test_auth_cookie_bearer_revocation_and_no_secret_leaks(api):
    headers = login(api, clear_cookie=False)
    response = api.client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["rol"] == "admin"
    users = api.client.get("/api/v1/usuarios").json()
    assert all("contrasenaHash" not in user for user in users)
    assert "pbkdf2" not in response.text
    with api.app.state.database.sessions() as db:
        session = db.scalar(select(Sesion))
        assert session.tokenHash not in headers["Authorization"]
        assert len(session.tokenHash) == 64
        assert session.tokenHash == token_hash(headers["Authorization"].split(" ", 1)[1])
    assert api.client.post("/api/v1/auth/logout", headers={"Origin": "http://testserver"}).status_code == 204
    assert api.client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert api.client.get("/api/v1/auth/me").status_code == 401


def test_bad_credentials_and_session_expiry(api):
    for email in ("admin@live.uleam.edu.ec", "missing@live.uleam.edu.ec"):
        result = api.client.post("/api/v1/auth/login", json={"correo": email, "contrasena": "wrong"})
        assert result.status_code == 401
        assert result.json()["detail"] == "Correo o contraseña incorrectos."
    headers = login(api)
    with api.app.state.database.sessions.begin() as db:
        db.scalar(select(Sesion)).expiraEn = now_ms() - 1
    assert api.client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_cookie_origin_checks_and_bearer_mobile(api):
    headers = login(api, clear_cookie=False)
    assert api.client.post("/api/v1/auth/logout").status_code == 403
    assert api.client.post("/api/v1/auth/logout", headers={"Origin": "https://hostile.example"}).status_code == 403
    result = api.client.post("/api/v1/auth/login", json={"correo": "admin@live.uleam.edu.ec", "contrasena": PASSWORD}, headers={"Origin": "https://hostile.example"})
    assert result.status_code == 403
    assert api.client.delete("/api/v1/misiones/1", headers={"Origin": "http://localhost:5173"}).status_code == 200
    # Native clients do not send browser Origin; their Bearer mutation is valid.
    assert api.client.delete("/api/v1/misiones/2", headers=headers).status_code == 200
    preflight = api.client.options("/api/v1/puntos", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_student_and_tutor_do_not_have_admin_rights(api):
    assert api.client.get("/api/v1/usuarios").status_code == 401
    for key in ("student", "tutor"):
        headers = login(api, key)
        for path in ("/api/v1/usuarios", f"/api/v1/usuarios/{api.users[key]}", "/api/v1/progreso", "/api/v1/misiones?incluirArchivadas=true"):
            assert api.client.get(path, headers=headers).status_code == 403
        assert api.client.delete("/api/v1/misiones/1", headers=headers).status_code == 403
        assert api.client.get("/api/v1/puntos", headers=headers).status_code == 200
        assert api.client.get("/api/v1/misiones", headers=headers).status_code == 200
    student = login(api, "student")
    assert api.client.get(f"/api/v1/usuarios/{api.users['student']}/progreso", headers=student).json() == []
    assert api.client.get(f"/api/v1/usuarios/{api.users['other']}/progreso", headers=student).status_code == 403
    assert api.client.post(f"/api/v1/usuarios/{api.users['other']}/progreso", json={"misionId": 1, "codigoQr": "CQ-BIB-001"}, headers=student).status_code == 403


def test_completion_is_idempotent_and_preserves_archived_history(api):
    student = login(api, "student")
    route = f"/api/v1/usuarios/{api.users['student']}/progreso"
    payload = {"misionId": 1, "codigoQr": "  cq-bib-001  "}
    first = api.client.post(route, json=payload, headers=student)
    assert first.status_code == 201
    assert first.json()["codigoQrValidado"] == "CQ-BIB-001"
    assert first.json()["fechaHora"] > 1_000_000_000_000
    repeated = api.client.post(route, json=payload, headers=student)
    assert repeated.status_code == 200
    assert repeated.json() == first.json()
    admin = login(api)
    assert api.client.delete("/api/v1/misiones/1", headers=admin).json()["activa"] is False
    assert 1 not in [m["id"] for m in api.client.get("/api/v1/misiones", headers=student).json()]
    assert any(m["id"] == 1 for m in api.client.get("/api/v1/misiones?incluirArchivadas=true", headers=admin).json())
    assert api.client.get(route, headers=student).json() == [first.json()]
    assert api.client.post(route, json=payload, headers=student).json() == first.json()
    user = api.client.get(f"/api/v1/usuarios/{api.users['student']}", headers=admin).json()
    assert (user["puntajeAcumulado"], user["nivel"]) == (50, 1)
    assert api.client.delete("/api/v1/puntos/1", headers=admin).status_code == 409


def test_invalid_qr_archived_mission_and_missing_resources(api):
    student = login(api, "student")
    route = f"/api/v1/usuarios/{api.users['student']}/progreso"
    assert api.client.post(route, json={"misionId": 1, "codigoQr": "wrong"}, headers=student).status_code == 422
    assert api.client.post(route, json={"misionId": 999, "codigoQr": "x"}, headers=student).status_code == 404
    admin = login(api)
    api.client.delete("/api/v1/misiones/1", headers=admin)
    assert api.client.post(route, json={"misionId": 1, "codigoQr": "CQ-BIB-001"}, headers=student).status_code == 409
    assert api.client.get("/api/v1/usuarios/999", headers=admin).status_code == 404
    assert api.client.get("/api/v1/usuarios/999/progreso", headers=admin).status_code == 404


def test_concurrent_completion_awards_once_and_keeps_all_totals(api):
    student = login(api, "student")
    route = f"/api/v1/usuarios/{api.users['student']}/progreso"
    def complete(mission_id):
        qr = {1: "CQ-BIB-001", 2: "CQ-SEC-002", 3: "CQ-LAB-003"}[mission_id]
        return api.client.post(route, json={"misionId": mission_id, "codigoQr": qr}, headers=student)
    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(complete, [1, 1, 1, 1, 2, 2, 3, 3]))
    assert [r.status_code for r in responses].count(201) == 3
    assert all(r.status_code in {200, 201} for r in responses)
    with api.app.state.database.sessions() as db:
        user = db.get(Usuario, api.users["student"])
        assert (user.puntajeAcumulado, user.nivel) == (160, 2)
        assert db.scalar(select(func.count(ProgresoMision.id))) == 3
