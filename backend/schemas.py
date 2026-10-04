from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Positivo = Annotated[int, Field(strict=True, gt=0, le=2147483647)]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class UsuarioPublico(Schema):
    id: int
    nombres: str
    correoInstitucional: str
    carrera: str
    puntajeAcumulado: int
    nivel: int
    rol: str

    @field_validator("correoInstitucional", mode="before")
    @classmethod
    def correo_visitante(cls, value):
        return value or ""


class Login(Schema):
    correo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=254)]
    contrasena: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class Registro(Schema):
    nombres: Nombre
    correo: Annotated[str, StringConstraints(strip_whitespace=True, max_length=254)]
    carrera: Nombre
    contrasena: Annotated[str, StringConstraints(min_length=8, max_length=256)]

    @field_validator("correo")
    @classmethod
    def correo_institucional(cls, value):
        import re
        value = value.lower()
        if not re.fullmatch(r"[^@\s]+@live\.uleam\.edu\.ec", value):
            raise ValueError("Usa tu correo institucional @live.uleam.edu.ec.")
        return value


class Visitante(Schema):
    nombres: Nombre


class SesionPublica(Schema):
    accessToken: str
    tokenType: Literal["bearer"] = "bearer"
    usuario: UsuarioPublico


class PuntoInput(Schema):
    nombre: Nombre
    categoria: Literal["Académico", "Trámites", "Servicios", "Recreación"]
    descripcion: Texto
    horarioAtencion: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
    tramites: Texto
    posX: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
    posY: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
    codigoQr: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]

    @field_validator("codigoQr")
    @classmethod
    def normalizar_qr(cls, value):
        return value.upper()


class PuntoPublico(PuntoInput):
    id: int


class MisionInput(Schema):
    titulo: Nombre
    descripcionPista: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    puntos: Positivo
    tiempoEstimadoMin: Positivo
    dificultad: Literal["Baja", "Media", "Alta"]
    puntoInteresId: Positivo
    insigniaNombre: Nombre
    insigniaEmoji: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
    activa: Annotated[bool, Field(strict=True)] = True


class MisionPublica(MisionInput):
    id: int


class CompletarMision(Schema):
    misionId: Positivo
    codigoQr: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]

    @field_validator("codigoQr")
    @classmethod
    def normalizar_qr(cls, value):
        return value.upper()


class ProgresoPublico(Schema):
    id: int
    usuarioId: int
    misionId: int
    fechaHora: int
    puntosObtenidos: int
    codigoQrValidado: str
    estado: Literal["completada"]
