from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = (CheckConstraint('"puntajeAcumulado" >= 0'), CheckConstraint("nivel >= 1"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombres: Mapped[str] = mapped_column(String(160))
    correoInstitucional: Mapped[str | None] = mapped_column(String(254), unique=True, nullable=True)
    carrera: Mapped[str] = mapped_column(String(160), default="")
    contrasenaHash: Mapped[str] = mapped_column(String(300), default="")
    puntajeAcumulado: Mapped[int] = mapped_column(Integer, default=0)
    nivel: Mapped[int] = mapped_column(Integer, default=1)
    rol: Mapped[str] = mapped_column(String(20), default="estudiante")


class PuntoInteres(Base):
    __tablename__ = "punto_interes"
    __table_args__ = (CheckConstraint('"posX" >= 0 AND "posX" <= 1'), CheckConstraint('"posY" >= 0 AND "posY" <= 1'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    categoria: Mapped[str] = mapped_column(String(30))
    descripcion: Mapped[str] = mapped_column(String(2000), default="")
    horarioAtencion: Mapped[str] = mapped_column(String(300), default="")
    tramites: Mapped[str] = mapped_column(String(2000), default="")
    posX: Mapped[float]
    posY: Mapped[float]
    codigoQr: Mapped[str] = mapped_column(String(128), unique=True)


class Mision(Base):
    __tablename__ = "mision"
    __table_args__ = (CheckConstraint("puntos > 0"), CheckConstraint('"tiempoEstimadoMin" > 0'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(160))
    descripcionPista: Mapped[str] = mapped_column(String(2000))
    puntos: Mapped[int] = mapped_column(Integer)
    tiempoEstimadoMin: Mapped[int] = mapped_column(Integer)
    dificultad: Mapped[str] = mapped_column(String(10))
    puntoInteresId: Mapped[int] = mapped_column(ForeignKey("punto_interes.id", ondelete="RESTRICT"), index=True)
    insigniaNombre: Mapped[str] = mapped_column(String(160))
    insigniaEmoji: Mapped[str] = mapped_column(String(32))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class ProgresoMision(Base):
    __tablename__ = "progreso_mision"
    __table_args__ = (UniqueConstraint("usuarioId", "misionId"), CheckConstraint('"puntosObtenidos" > 0'))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuarioId: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"), index=True)
    misionId: Mapped[int] = mapped_column(ForeignKey("mision.id", ondelete="RESTRICT"), index=True)
    fechaHora: Mapped[int] = mapped_column(BigInteger)
    puntosObtenidos: Mapped[int] = mapped_column(Integer)
    codigoQrValidado: Mapped[str] = mapped_column(String(128))
    estado: Mapped[str] = mapped_column(String(20), default="completada")


class Sesion(Base):
    __tablename__ = "sesion"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tokenHash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    usuarioId: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    expiraEn: Mapped[int] = mapped_column(BigInteger)
