# Contrato FastAPI · v1

Prefijo: `/api/v1`. El servidor genera la documentación interactiva en `/docs`
y el esquema completo en `/openapi.json`. Ese esquema es la referencia exacta
de campos, tipos y límites.

## Autenticación

```http
POST /api/v1/auth/login
Content-Type: application/json

{"correo":"admin@tu-universidad.edu","contrasena":"tu-contraseña"}
```

Respuesta:

```json
{
  "accessToken": "token-aleatorio",
  "tokenType": "bearer",
  "usuario": {
    "id": 1,
    "nombres": "Administrador Campus Quest",
    "correoInstitucional": "admin@tu-universidad.edu",
    "carrera": "Administración",
    "puntajeAcumulado": 0,
    "nivel": 1,
    "rol": "admin"
  }
}
```

Web: recibe además `Set-Cookie: campusquest_session=...; HttpOnly; SameSite=Lax`.
El navegador envía esa cookie con `credentials: 'include'`. Con HTTPS y
`COOKIE_SECURE=true` también se agrega Secure. Android usará el `accessToken`
como Bearer. No se debe guardar una contraseña o token en el repositorio.

`GET /auth/me` devuelve el perfil de la sesión; `POST /auth/logout` revoca el
token y responde 204. Un estudiante autenticado no obtiene acceso al panel por
iniciar sesión: los endpoints administrativos siguen devolviendo 403.

## Endpoints

Todas las rutas de esta tabla llevan el prefijo `/api/v1`.

| Método | Ruta | Permiso y resultado |
|---|---|---|
| GET | `/health` | Público: `{ "status": "ok" }`, comprueba la BD |
| POST | `/auth/login` | Login; objeto de sesión |
| GET | `/auth/me` | Autenticado; perfil sin hash |
| POST | `/auth/logout` | Autenticado; 204 |
| GET | `/usuarios` | Admin; array de usuarios |
| GET | `/usuarios/{id}` | Admin; perfil |
| GET | `/puntos` | Autenticado; array |
| POST | `/puntos` | Admin; objeto creado, 201 |
| PUT | `/puntos/{id}` | Admin; objeto actualizado, 200 |
| DELETE | `/puntos/{id}` | Admin; 204 o 409 si tiene misiones |
| GET | `/misiones` | Autenticado; solo activas |
| GET | `/misiones?incluirArchivadas=true` | Admin; catálogo completo |
| POST | `/misiones` | Admin; objeto creado, 201 |
| PUT | `/misiones/{id}` | Admin; objeto actualizado, 200 |
| DELETE | `/misiones/{id}` | Admin; objeto archivado, 200 |
| GET | `/progreso` | Admin; array global, ordenado por fecha descendente |
| GET | `/usuarios/{id}/progreso` | Admin o titular estudiante/visitante; array |
| POST | `/usuarios/{id}/progreso` | Admin o titular; registro idempotente |

No existe todavía registro público ni creación de cuentas móviles por API.
Las cuentas de demo no tienen contraseña y no se pueden usar para login.

## Misión

POST y PUT reciben todos estos campos, **sin `id`**. PUT es reemplazo completo,
no una actualización parcial.

```json
{
  "titulo": "Encuentra la biblioteca",
  "descripcionPista": "Bloque B, planta baja. Escanea el QR del mostrador.",
  "puntos": 50,
  "tiempoEstimadoMin": 15,
  "dificultad": "Media",
  "puntoInteresId": 1,
  "insigniaNombre": "Ratón de biblioteca",
  "insigniaEmoji": "📚",
  "activa": true
}
```

Respuesta: esos campos más `id`. Dificultad: `Baja`, `Media` o `Alta`.
`puntos` y `tiempoEstimadoMin` son enteros positivos. El punto debe existir.
La web establece límites de edición de 10 000 XP y 1 440 minutos; el contrato
servidor admite enteros positivos compatibles con Android. Los valores no
pueden modificar el progreso que ya se registró.

Reactivar se hace mediante PUT del objeto completo con `activa=true`.
Archivar mediante DELETE equivale a `activa=false`; no elimina registros.

## Punto del campus

```json
{
  "nombre": "Biblioteca central",
  "categoria": "Académico",
  "descripcion": "Sala de lectura y préstamo de libros.",
  "horarioAtencion": "Lunes a viernes, 07:30 a 19:00",
  "tramites": "Préstamo y devolución de libros",
  "posX": 0.22,
  "posY": 0.30,
  "codigoQr": "CQ-BIB-001"
}
```

Categorías: `Académico`, `Trámites`, `Servicios`, `Recreación`. Coordenadas
finitas entre 0 y 1. QR normalizado a mayúsculas, sin espacios en los extremos,
único por punto. POST y PUT reciben el objeto sin `id`.

## Progreso: reintentos sin duplicados

```http
POST /api/v1/usuarios/12/progreso
Authorization: Bearer token-del-usuario-12
Content-Type: application/json

{"misionId":1,"codigoQr":"CQ-BIB-001"}
```

Primera vez: 201 y el evento:

```json
{
  "id": 31,
  "usuarioId": 12,
  "misionId": 1,
  "fechaHora": 1790874000000,
  "puntosObtenidos": 50,
  "codigoQrValidado": "CQ-BIB-001",
  "estado": "completada"
}
```

Repetir la misma misión con el mismo QR correcto devuelve **200 y el evento
original**, con la misma fecha y puntos. No vuelve a sumar. Un QR distinto
produce 422. Una misión archivada sin progreso previo produce 409. El usuario
no puede enviar fecha, puntos ni operar sobre otro ID.

## Errores

- 401: falta sesión, credenciales incorrectas, expiración o revocación.
- 403: rol insuficiente, usuario ajeno u Origin no autorizado.
- 404: recurso o ruta inexistente.
- 409: QR duplicado, relación incompatible o misión archivada.
- 422: campos inválidos o QR incorrecto.

Los errores de negocio devuelven `{ "detail": "mensaje" }`. Los de validación
Pydantic devuelven `detail` como array con `loc` y `msg`. El frontend interpreta
ambos formatos. Las rutas API desconocidas nunca devuelven el HTML de la SPA.

Las llamadas de herramientas HTTP pueden usar Bearer para no depender de
cookies y Origin. Para probar una mutación con cookie desde `curl`, agrega un
`Origin` autorizado; un cliente sin esa cabecera recibe 403.

## Integración móvil

- `POST /api/v1/auth/register`: `{nombres, correo, carrera, contrasena}`.
  Correo `@live.uleam.edu.ec`, contraseña 8–256 caracteres. Devuelve 201 y
  `{accessToken, tokenType, usuario}`; el rol siempre es `estudiante`.
  Un correo ya registrado devuelve 409. No verifica propiedad del correo.
- `POST /api/v1/auth/visitor`: `{nombres}`. Devuelve 201 y una sesión de
  visitante nueva. Un nombre repetido nunca recupera una cuenta existente.
- `GET /api/v1/catalogo`: autenticado; catálogo activo más misiones archivadas
  completadas por el usuario actual, para conservar su historial.
- `GET /api/v1/ranking`: autenticado; hasta 100 estudiantes/visitantes,
  ordenados por puntos, con `{id, nombres, puntajeAcumulado, nivel}`.

Android envía `Authorization: Bearer <accessToken>` y se conecta directamente
al origen Render; el panel web conserva cookies a través de Vercel.
