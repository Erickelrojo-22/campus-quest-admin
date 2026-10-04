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


def test_point_crud_normalizes_qr_and_enforces_uniqueness(api):
    admin = login(api)
    body = point_body(api, admin)
    duplicate = {**body, "codigoQr": "  cq-bib-001  "}
    assert api.client.post("/api/v1/puntos", json=duplicate, headers=admin).status_code == 409
    created = api.client.post("/api/v1/puntos", json={**body, "nombre": "Nuevo punto", "codigoQr": " cq-new-009 "}, headers=admin)
    assert created.status_code == 201
    assert created.json()["codigoQr"] == "CQ-NEW-009"
    point_id = created.json()["id"]
    assert api.client.put(f"/api/v1/puntos/{point_id}", json=duplicate, headers=admin).status_code == 409
    assert api.client.delete(f"/api/v1/puntos/{point_id}", headers=admin).status_code == 204


@pytest.mark.parametrize("field,value", [("puntos", 0), ("puntos", -1), ("puntos", True), ("puntos", "30"), ("tiempoEstimadoMin", 0), ("dificultad", "Extrema"), ("titulo", " "), ("activa", "true")])
def test_mission_validation(api, field, value):
    admin = login(api)
    body = mission_body(api, admin)
    assert api.client.post("/api/v1/misiones", json={**body, field: value}, headers=admin).status_code == 422


@pytest.mark.parametrize("field,value", [("posX", -0.1), ("posY", 1.1), ("posX", True), ("categoria", "Otro"), ("codigoQr", " ")])
def test_point_validation(api, field, value):
    admin = login(api)
    body = point_body(api, admin)
    assert api.client.post("/api/v1/puntos", json={**body, field: value}, headers=admin).status_code == 422


def test_mission_edits_do_not_rewrite_points_or_move_completed_history(api):
    student = login(api, "student")
    route = f"/api/v1/usuarios/{api.users['student']}/progreso"
    api.client.post(route, json={"misionId": 1, "codigoQr": "CQ-BIB-001"}, headers=student)
    admin = login(api)
    body = mission_body(api, admin)
    assert api.client.put("/api/v1/misiones/1", json={**body, "puntoInteresId": 2}, headers=admin).status_code == 409
    assert api.client.put("/api/v1/misiones/1", json={**body, "puntos": 100}, headers=admin).status_code == 200
    assert api.client.get(route, headers=student).json()[0]["puntosObtenidos"] == 50
    assert api.client.post("/api/v1/misiones", json={**body, "puntoInteresId": 999}, headers=admin).status_code == 404
    assert api.client.post("/api/v1/misiones", json={**body, "id": 99}, headers=admin).status_code == 422


def test_cli_demo_is_explicit_idempotent_and_without_passwords(api):
    database = api.app.state.database
    seed_demo(database)
    seed_demo(database)
    with database.sessions() as db:
        demos = db.scalars(select(Usuario).where(Usuario.correoInstitucional.like("demo.%"))).all()
        assert len(demos) == 12
        assert all(u.rol == "estudiante" and not u.contrasenaHash for u in demos)
        for user in demos:
            total = db.scalar(select(func.coalesce(func.sum(ProgresoMision.puntosObtenidos), 0)).where(ProgresoMision.usuarioId == user.id))
            assert user.puntajeAcumulado == total
            assert user.nivel == 1 + total // 100
    with pytest.raises(ValueError, match="Ya existe"):
        create_admin(database, "admin@live.uleam.edu.ec", PASSWORD)


def test_production_requires_secure_cookies_and_exact_cors():
    with pytest.raises(ValueError, match="COOKIE_SECURE"):
        Settings(app_env="production", cookie_secure=False)
    with pytest.raises(ValueError, match="explícitos"):
        Settings(allowed_origins=("*",))


def test_cookie_httponly_samesite_and_cli_password_bounds(api):
    response = api.client.post("/api/v1/auth/login", json={"correo": "admin@live.uleam.edu.ec", "contrasena": PASSWORD})
    cookie = response.headers["set-cookie"]
    assert COOKIE_NAME in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    for email, password in (("@", PASSWORD), ("someone@example.com", "x" * 257), ("someone@example.com", "short")):
        with pytest.raises(ValueError, match="correo válido"):
            create_admin(api.app.state.database, email, password)


def test_database_foreign_keys_and_duplicate_progress_are_enforced(api):
    from sqlalchemy.exc import IntegrityError
    database = api.app.state.database
    raw = {"usuarioId": api.users["student"], "misionId": 1, "fechaHora": now_ms(), "puntosObtenidos": 50, "codigoQrValidado": "CQ-BIB-001", "estado": "completada"}
    with database.sessions.begin() as db:
        db.add(ProgresoMision(**raw))
    with pytest.raises(IntegrityError):
        with database.sessions.begin() as db:
            db.add(ProgresoMision(**raw))
    with pytest.raises(IntegrityError):
        with database.sessions.begin() as db:
            db.add(ProgresoMision(**{**raw, "usuarioId": 99999}))


def test_mobile_registration_creates_student_and_login_preserves_password_spaces(api):
    password = "  Mobile_password_123  "
    response = api.client.post("/api/v1/auth/register", json={
        "nombres": "Estudiante remoto", "correo": " NEW@live.uleam.edu.ec ",
        "carrera": "Software", "contrasena": password,
    })
    assert response.status_code == 201
    body = response.json()
    assert body["usuario"]["rol"] == "estudiante"
    assert body["usuario"]["puntajeAcumulado"] == 0
    assert "contrasenaHash" not in body["usuario"]
    api.client.cookies.clear()
    headers = {"Authorization": "Bearer " + body["accessToken"]}
    assert api.client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert api.client.get("/api/v1/usuarios", headers=headers).status_code == 403
    duplicate = api.client.post("/api/v1/auth/register", json={
        "nombres": "Otra persona", "correo": "new@live.uleam.edu.ec",
        "carrera": "Software", "contrasena": password,
    })
    assert duplicate.status_code == 409
    assert api.client.post("/api/v1/auth/login", json={"correo": "new@live.uleam.edu.ec", "contrasena": password}).status_code == 200


def test_mobile_registration_rejects_roles_and_noninstitutional_email(api):
    payload = {"nombres": "Alumno", "correo": "user@example.com", "carrera": "Software", "contrasena": "password123"}
    assert api.client.post("/api/v1/auth/register", json=payload).status_code == 422
    payload.update(correo="user@live.uleam.edu.ec", rol="admin")
    assert api.client.post("/api/v1/auth/register", json=payload).status_code == 422
    payload.pop("rol")
    payload["contrasena"] = "short"
    assert api.client.post("/api/v1/auth/register", json=payload).status_code == 422


def test_visitors_with_same_name_are_distinct_and_cannot_take_over_accounts(api):
    first = api.client.post("/api/v1/auth/visitor", json={"nombres": "Admin"})
    assert first.status_code == 201
    api.client.cookies.clear()
    second = api.client.post("/api/v1/auth/visitor", json={"nombres": "Admin"})
    assert second.status_code == 201
    one, two = first.json(), second.json()
    assert one["usuario"]["id"] != two["usuario"]["id"]
    assert one["usuario"]["rol"] == "visitante"
    api.client.cookies.clear()
    headers = {"Authorization": "Bearer " + one["accessToken"]}
    assert api.client.get(f'/api/v1/usuarios/{two["usuario"]["id"]}/progreso', headers=headers).status_code == 403
    from backend.models import Mision, PuntoInteres
    with api.app.state.database.sessions() as db:
        code = db.get(PuntoInteres, db.get(Mision, 1).puntoInteresId).codigoQr
    assert api.client.post(f'/api/v1/usuarios/{one["usuario"]["id"]}/progreso', json={"misionId": 1, "codigoQr": code}, headers=headers).status_code == 201


def test_personal_catalog_keeps_completed_archived_missions_only(api):
    from backend.models import PuntoInteres, Mision
    student = login(api, "student")
    with api.app.state.database.sessions() as db:
        code = db.get(PuntoInteres, db.get(Mision, 1).puntoInteresId).codigoQr
    assert api.client.post(f'/api/v1/usuarios/{api.users["student"]}/progreso', json={"misionId": 1, "codigoQr": code}, headers=student).status_code == 201
    admin = login(api)
    for id in (1, 2):
        assert api.client.delete(f"/api/v1/misiones/{id}", headers=admin).status_code == 200
    catalog = api.client.get("/api/v1/catalogo", headers=student).json()
    assert any(m["id"] == 1 and not m["activa"] for m in catalog)
    assert not any(m["id"] == 2 for m in catalog)


def test_ranking_exposes_no_credentials_or_emails(api):
    response = api.client.get("/api/v1/ranking", headers=login(api, "student"))
    assert response.status_code == 200
    assert response.json()
    assert all(set(u) == {"id", "nombres", "puntajeAcumulado", "nivel"} for u in response.json())
    assert all(u["id"] != api.users["admin"] for u in response.json())
    api.client.cookies.clear()
    assert api.client.get("/api/v1/ranking").status_code == 401


def test_mobile_auth_rejects_foreign_browser_origin(api):
    for path, payload in [
        ("visitor", {"nombres": "Visitante"}),
        ("register", {"nombres": "Estudiante", "correo": "new@live.uleam.edu.ec", "carrera": "Software", "contrasena": "password123"}),
    ]:
        assert api.client.post(f"/api/v1/auth/{path}", json=payload, headers={"Origin": "https://hostile.example"}).status_code == 403
