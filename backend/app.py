import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import Settings
from .database import Database
from .models import Mision, ProgresoMision, PuntoInteres, Sesion, Usuario
from .schemas import CompletarMision, Login, Registro, Visitante, MisionInput, MisionPublica, ProgresoPublico, PuntoInput, PuntoPublico, SesionPublica, UsuarioPublico
from .security import COOKIE_NAME, AuthContext, current_auth, hash_password, now_ms, require_admin, require_owner, token_hash, verify_password


def get_db(request: Request):
    with request.app.state.database.sessions() as db:
        yield db


def get_or_404(db: Session, model, identifier: int):
    item = db.get(model, identifier)
    if item is None:
        raise HTTPException(404, "No se encontró el recurso solicitado.")
    return item


def commit_or_conflict(db: Session, message: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, message) from None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    database = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app):
        database.initialize()
        yield
        database.engine.dispose()

    app = FastAPI(title="Campus Quest API", version="1.0.0", lifespan=lifespan)
    app.state.database = database
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def protect_cookie_mutations(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            same_origin = f"{request.url.scheme}://{request.url.netloc}"
            allowed = {same_origin, *settings.allowed_origins}
            bearer = request.headers.get("authorization", "").lower().startswith("bearer ")
            cookie_auth = bool(request.cookies.get(COOKIE_NAME)) and not bearer
            is_login = request.url.path in {"/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/visitor"}
            if (cookie_auth and not origin) or ((cookie_auth or is_login) and origin and origin not in allowed):
                return JSONResponse(status_code=403, content={"detail": "Origen no permitido para esta operación."})
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/v1/health")
    def health(db: Session = Depends(get_db)):
        db.execute(text("SELECT 1"))
        return {"status": "ok"}

    def open_session(user: Usuario, response: Response, db: Session):
        token = secrets.token_urlsafe(48)
        db.add(Sesion(tokenHash=token_hash(token), usuarioId=user.id, expiraEn=now_ms() + settings.session_ttl_hours * 3_600_000))
        db.commit()
        response.set_cookie(COOKIE_NAME, token, max_age=settings.session_ttl_hours * 3600, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")
        return SesionPublica(accessToken=token, usuario=UsuarioPublico.model_validate(user))

    @app.post("/api/v1/auth/login", response_model=SesionPublica)
    def login(body: Login, response: Response, db: Session = Depends(get_db)):
        user = db.scalar(select(Usuario).where(Usuario.correoInstitucional == body.correo.lower()))
        dummy_hash = "pbkdf2-sha256$600000$" + "00" * 16 + "$" + "00" * 32
        valid = verify_password(body.contrasena, user.contrasenaHash if user else dummy_hash)
        if user is None or not valid:
            raise HTTPException(401, "Correo o contraseña incorrectos.")
        return open_session(user, response, db)

    @app.post("/api/v1/auth/register", response_model=SesionPublica, status_code=201)
    def register(body: Registro, response: Response, db: Session = Depends(get_db)):
        user = Usuario(nombres=body.nombres, correoInstitucional=body.correo, carrera=body.carrera,
                       contrasenaHash=hash_password(body.contrasena), rol="estudiante")
        db.add(user)
        # Flush keeps account creation and its first session in one transaction.
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Ya existe una cuenta con ese correo.") from None
        return open_session(user, response, db)

    @app.post("/api/v1/auth/visitor", response_model=SesionPublica, status_code=201)
    def visitor(body: Visitante, response: Response, db: Session = Depends(get_db)):
        # Names are labels, never proof of ownership of an existing account.
        user = Usuario(nombres=body.nombres, correoInstitucional=None, carrera="", rol="visitante")
        db.add(user)
        db.flush()
        return open_session(user, response, db)

    @app.get("/api/v1/ranking")
    def ranking(_auth: AuthContext = Depends(current_auth), db: Session = Depends(get_db)):
        users = db.scalars(select(Usuario).where(Usuario.rol.in_(["estudiante", "visitante"]))
                           .order_by(Usuario.puntajeAcumulado.desc(), Usuario.id).limit(100)).all()
        return [{"id": u.id, "nombres": u.nombres, "puntajeAcumulado": u.puntajeAcumulado,
                 "nivel": u.nivel} for u in users]

    @app.get("/api/v1/catalogo", response_model=list[MisionPublica])
    def personal_catalog(auth: AuthContext = Depends(current_auth), db: Session = Depends(get_db)):
        completed = select(ProgresoMision.misionId).where(ProgresoMision.usuarioId == auth.usuario.id)
        return db.scalars(select(Mision).where(Mision.activa.is_(True) | Mision.id.in_(completed))
                          .order_by(Mision.id)).all()

    @app.get("/api/v1/auth/me", response_model=UsuarioPublico)
    def me(auth: AuthContext = Depends(current_auth)):
        return auth.usuario

    @app.post("/api/v1/auth/logout", status_code=204)
    def logout(response: Response, auth: AuthContext = Depends(current_auth), db: Session = Depends(get_db)):
        db.execute(delete(Sesion).where(Sesion.tokenHash == auth.token_hash))
        db.commit()
        response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=settings.cookie_secure, samesite="lax")

    @app.get("/api/v1/usuarios", response_model=list[UsuarioPublico])
    def users(_auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
        return db.scalars(select(Usuario).order_by(Usuario.nombres, Usuario.id)).all()

    @app.get("/api/v1/usuarios/{usuario_id}", response_model=UsuarioPublico)
    def user_profile(usuario_id: int, _auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
        return get_or_404(db, Usuario, usuario_id)

    @app.get("/api/v1/puntos", response_model=list[PuntoPublico])
    def points(_auth: AuthContext = Depends(current_auth), db: Session = Depends(get_db)):
        return db.scalars(select(PuntoInteres).order_by(PuntoInteres.id)).all()

    @app.post("/api/v1/puntos", response_model=PuntoPublico, status_code=201)
    def create_point(body: PuntoInput, _auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
        point = PuntoInteres(**body.model_dump())
        db.add(point)
        commit_or_conflict(db, "Ya existe un punto con ese código QR.")
        return point

    @app.put("/api/v1/puntos/{punto_id}", response_model=PuntoPublico)
    def update_point(punto_id: int, body: PuntoInput, _auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
        point = get_or_404(db, PuntoInteres, punto_id)
        for field, value in body.model_dump().items():
            setattr(point, field, value)
        commit_or_conflict(db, "Ya existe un punto con ese código QR.")
        return point

    @app.delete("/api/v1/puntos/{punto_id}", status_code=204)
    def delete_point(punto_id: int, _auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
        point = get_or_404(db, PuntoInteres, punto_id)
        if db.scalar(select(Mision.id).where(Mision.puntoInteresId == punto_id).limit(1)):
            raise HTTPException(409, "El punto tiene misiones asociadas; conserva su historial.")
        db.delete(point)
        commit_or_conflict(db, "El punto tiene misiones asociadas.")

    @app.get("/api/v1/misiones", response_model=list[MisionPublica])
    def missions(incluirArchivadas: bool = False, auth: AuthContext = Depends(current_auth), db: Session = Depends(get_db)):
        if incluirArchivadas and auth.usuario.rol != "admin":
            raise HTTPException(403, "Solo administración puede consultar misiones archivadas.")
        query = select(Mision).order_by(Mision.id)
        if not incluirArchivadas:
            query = query.where(Mision.activa.is_(True))
        return db.scalars(query).all()

    @app.post("/api/v1/misiones", response_model=MisionPublica, status_code=201)
    def create_mission(body: MisionInput, _auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
        get_or_404(db, PuntoInteres, body.puntoInteresId)
        mission = Mision(**body.model_dump())
        db.add(mission)
        commit_or_conflict(db, "No se pudo crear la misión con ese punto.")
        return mission

    @app.put("/api/v1/misiones/{mision_id}", response_model=MisionPublica)
    def update_mission(mision_id: int, body: MisionInput, _auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
        if db.bind.dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        mission = db.scalar(select(Mision).where(Mision.id == mision_id).with_for_update())
        if mission is None:
            raise HTTPException(404, "No se encontró la misión.")
        get_or_404(db, PuntoInteres, body.puntoInteresId)
        if body.puntoInteresId != mission.puntoInteresId and db.scalar(select(ProgresoMision.id).where(ProgresoMision.misionId == mision_id).limit(1)):
            raise HTTPException(409, "Una misión con progreso no puede cambiar de lugar.")
        for field, value in body.model_dump().items():
            setattr(mission, field, value)
        commit_or_conflict(db, "No se pudo actualizar la misión.")
        return mission

    @app.delete("/api/v1/misiones/{mision_id}", response_model=MisionPublica)
    def archive_mission(mision_id: int, _auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
        mission = get_or_404(db, Mision, mision_id)
        mission.activa = False
        db.commit()
        return mission

    @app.get("/api/v1/progreso", response_model=list[ProgresoPublico])
    def progress_all(_auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
        return db.scalars(select(ProgresoMision).order_by(ProgresoMision.fechaHora.desc(), ProgresoMision.id.desc())).all()

    @app.get("/api/v1/usuarios/{usuario_id}/progreso", response_model=list[ProgresoPublico])
    def progress_user(usuario_id: int, auth: AuthContext = Depends(current_auth), db: Session = Depends(get_db)):
        require_owner(auth, usuario_id)
        get_or_404(db, Usuario, usuario_id)
        return db.scalars(select(ProgresoMision).where(ProgresoMision.usuarioId == usuario_id).order_by(ProgresoMision.fechaHora.desc(), ProgresoMision.id.desc())).all()

    @app.post("/api/v1/usuarios/{usuario_id}/progreso", response_model=ProgresoPublico, status_code=201)
    def complete_mission(usuario_id: int, body: CompletarMision, response: Response, auth: AuthContext = Depends(current_auth), db: Session = Depends(get_db)):
        require_owner(auth, usuario_id)
        # SQLite serializes competing writes before any reads. PostgreSQL locks the
        # user's row, so distinct missions also cannot overwrite accumulated points.
        if db.bind.dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        user = db.scalar(select(Usuario).where(Usuario.id == usuario_id).with_for_update())
        if user is None:
            raise HTTPException(404, "No se encontró el usuario.")
        previous = db.scalar(select(ProgresoMision).where(ProgresoMision.usuarioId == usuario_id, ProgresoMision.misionId == body.misionId))
        if previous:
            if previous.codigoQrValidado != body.codigoQr:
                raise HTTPException(422, "El código QR no corresponde a esta misión.")
            response.status_code = 200
            return previous
        mission = db.scalar(select(Mision).where(Mision.id == body.misionId).with_for_update())
        if mission is None:
            raise HTTPException(404, "No se encontró la misión.")
        if not mission.activa:
            raise HTTPException(409, "La misión está archivada.")
        point = get_or_404(db, PuntoInteres, mission.puntoInteresId)
        if point.codigoQr != body.codigoQr:
            raise HTTPException(422, "El código QR no corresponde a esta misión.")
        event = ProgresoMision(usuarioId=user.id, misionId=mission.id, fechaHora=now_ms(), puntosObtenidos=mission.puntos, codigoQrValidado=body.codigoQr, estado="completada")
        if user.puntajeAcumulado + mission.puntos > 2_147_483_647:
            raise HTTPException(409, "El puntaje supera el límite compatible con Android.")
        db.add(event)
        user.puntajeAcumulado += mission.puntos
        user.nivel = 1 + user.puntajeAcumulado // 100
        commit_or_conflict(db, "La misión ya se completó; vuelve a consultar el progreso.")
        return event

    @app.api_route("/api/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
    def unknown_api(path: str):
        raise HTTPException(404, "Ruta API no encontrada.")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.split("/", 1)[0] in {"api", "docs", "redoc", "openapi.json"}:
            raise HTTPException(404, "Ruta no encontrada.")
        root = Path(settings.frontend_dist_dir).resolve()
        candidate = (root / path).resolve()
        if not candidate.is_relative_to(root):
            raise HTTPException(404, "Recurso no encontrado.")
        if candidate.is_file():
            return FileResponse(candidate)
        if Path(path).suffix or path.startswith("assets/"):
            raise HTTPException(404, "Recurso no encontrado.")
        index = root / "index.html"
        if not index.is_file():
            raise HTTPException(404, "Compila el frontend para servir el dashboard.")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
