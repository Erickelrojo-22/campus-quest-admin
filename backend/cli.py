import argparse
import getpass
import json
import os
import random
import re
from pathlib import Path

from sqlalchemy import select

from .config import Settings
from .database import Database
from .models import Mision, ProgresoMision, PuntoInteres, Usuario
from .security import hash_password, now_ms


def seed_catalog(db):
    """Insert the original Android catalog once without depending on frontend."""
    catalog = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
    for raw in catalog["puntos"]:
        if db.get(PuntoInteres, raw["id"]) is None:
            if db.scalar(select(PuntoInteres).where(PuntoInteres.codigoQr == raw["codigoQr"])):
                raise ValueError("Conflicto de catálogo: un QR original ya usa otro ID.")
            db.add(PuntoInteres(**raw))
    db.flush()
    for raw in catalog["misiones"]:
        if db.get(Mision, raw["id"]) is None:
            db.add(Mision(**raw))
    db.flush()
    # PostgreSQL sequences do not advance after explicit Android seed IDs.
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        for table in ("punto_interes", "mision"):
            db.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT MAX(id) FROM {table}), 1), true)"))


def create_admin(database: Database, email: str, password: str, name: str = "Administrador Campus Quest"):
    email = email.strip().lower()
    name = name.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(email) > 254 or not 8 <= len(password) <= 256:
        raise ValueError("Usa un correo válido y una contraseña de 8 a 256 caracteres.")
    if not 1 <= len(name) <= 160:
        raise ValueError("El nombre del administrador debe tener de 1 a 160 caracteres.")
    with database.sessions.begin() as db:
        if db.scalar(select(Usuario).where(Usuario.correoInstitucional == email)):
            raise ValueError("Ya existe ese correo. No se cambia su rol ni contraseña automáticamente.")
        db.add(Usuario(nombres=name, correoInstitucional=email, carrera="Administración", contrasenaHash=hash_password(password), rol="admin"))


def seed_demo(database: Database):
    """Explicit demo participants only: none has a password or administrative role."""
    people = [
        ("Sofía Mendoza", "Ingeniería de Software", [1, 3, 8, 5, 2, 4, 7, 6]),
        ("Mateo García", "Medicina", [1, 2, 4, 5, 7]),
        ("Valentina Rojas", "Arquitectura", [1, 3, 5, 6]),
        ("Diego Zambrano", "Ingeniería de Software", [3, 8, 1]),
        ("Camila Vélez", "Administración de Empresas", [1, 2, 7]),
        ("Sebastián Moreira", "Comunicación", [5, 6, 4]),
        ("Daniela Cedeño", "Medicina", [1, 4]),
        ("Andrés Ponce", "Ingeniería Civil", [3, 6]),
        ("Isabella Torres", "Arquitectura", [1]),
        ("Nicolás Vera", "Administración de Empresas", [2, 7]),
        ("Lucía Delgado", "Ingeniería de Software", [8]),
        ("Gabriel Alcívar", "Comunicación", []),
    ]
    rng = random.Random(42)
    with database.sessions.begin() as db:
        seed_catalog(db)
        for index, (name, career, mission_ids) in enumerate(people, start=1):
            email = f"demo.{index}@live.uleam.edu.ec"
            if db.scalar(select(Usuario).where(Usuario.correoInstitucional == email)):
                continue
            user = Usuario(nombres=name, correoInstitucional=email, carrera=career, contrasenaHash="", rol="estudiante", puntajeAcumulado=0, nivel=1)
            db.add(user)
            db.flush()
            for mission_id in mission_ids:
                mission = db.get(Mision, mission_id)
                point = db.get(PuntoInteres, mission.puntoInteresId)
                user.puntajeAcumulado += mission.puntos
                event_time = now_ms() - rng.randint(0, 6) * 86_400_000 - rng.randint(0, 12) * 3_600_000
                db.add(ProgresoMision(usuarioId=user.id, misionId=mission.id, fechaHora=event_time, puntosObtenidos=mission.puntos, codigoQrValidado=point.codigoQr, estado="completada"))
            user.nivel = 1 + user.puntajeAcumulado // 100


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inicialización y administración de Campus Quest")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Crear tablas e insertar catálogo Android sin usuarios demo")
    admin = commands.add_parser("create-admin", help="Crear administrador sin contraseña constante")
    admin.add_argument("--email", default=os.getenv("ADMIN_EMAIL"))
    admin.add_argument("--name", default="Administrador Campus Quest")
    commands.add_parser("seed-demo", help="Insertar participantes/progreso ficticios explícitamente")
    args = parser.parse_args(argv)
    database = Database(Settings().database_url)
    database.initialize()
    try:
        if args.command == "init":
            with database.sessions.begin() as db:
                seed_catalog(db)
            print("Base de datos y catálogo Android inicializados.")
        elif args.command == "create-admin":
            if not args.email:
                parser.error("Indica --email o configura ADMIN_EMAIL.")
            password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Contraseña del administrador: ")
            create_admin(database, args.email, password, args.name)
            print("Administrador creado.")
        elif args.command == "seed-demo":
            seed_demo(database)
            print("Participantes y progreso de demostración insertados.")
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")
    finally:
        database.engine.dispose()


if __name__ == "__main__":
    main()
