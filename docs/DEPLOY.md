# Despliegue y mantenimiento

## Railway + Vercel

Este es el despliegue previsto para el proyecto. El repositorio contiene dos
servicios: Railway ejecuta FastAPI y Vercel compila `frontend/` con Vite.

```mermaid
flowchart LR
    N[Navegador] -->|mismo origen /api/v1| V[Vercel: React + proxy]
    V -->|HTTPS, Cookie y Origin| R[Railway: FastAPI]
    R --> P[(PostgreSQL Railway)]
    A[Android · próxima etapa] -.->|HTTPS + Bearer| R
```

### 1. Preparar Railway

1. Crea un proyecto Railway y agrega PostgreSQL.
2. Agrega un servicio desde este repositorio GitHub. Mantén **Root Directory
   en la raíz**, porque `requirements.txt` y `Dockerfile.backend` están allí.
3. Configura `RAILWAY_DOCKERFILE_PATH=Dockerfile.backend` antes de construir.
   Este Dockerfile solo instala y ejecuta FastAPI; no construye React.
4. Agrega variables:

   ```dotenv
   RAILWAY_DOCKERFILE_PATH=Dockerfile.backend
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   APP_ENV=production
   COOKIE_SECURE=true
   SESSION_TTL_HOURS=24
   ALLOWED_ORIGINS=https://tu-dashboard.vercel.app
   ```

   Selecciona la referencia a `DATABASE_URL` del servicio PostgreSQL real. Si
   se llama distinto, adapta `Postgres`. El backend normaliza una URL
   `postgresql://` a `postgresql+psycopg://` automáticamente. No pegues esta
   contraseña en las variables frontend.

5. En Deploy, configura **Healthcheck Path** `/api/v1/health`. El CMD del
   Dockerfile escucha `PORT`, que Railway inyecta. Deja Start Command vacío
   para reutilizar ese CMD.
6. En la primera instalación, configura **Pre-deploy Command**:

   ```bash
   python -m backend.cli init
   ```

   Inicializa tablas y catálogo, sin administrador ni usuarios demo. Después
   puedes retirarlo; las versiones con cambios de esquema requerirán
   migraciones Alembic, no simplemente volver a ejecutar `create_all`.
7. Genera un dominio público del servicio, por ejemplo
   `https://tu-backend.up.railway.app`. Comprueba:

   ```text
   https://tu-backend.up.railway.app/api/v1/health
   https://tu-backend.up.railway.app/docs
   ```

   La raíz de Railway puede devolver 404: el frontend está en Vercel, y eso
   es correcto. Usa `/api/v1/health` para comprobar la API.

El builder y el puerto siguen las guías oficiales de
[Dockerfiles Railway](https://docs.railway.com/builds/dockerfiles) y
[healthchecks](https://docs.railway.com/deployments/healthchecks).
La guía usa Docker y Settings del servicio; no depende del antiguo
`railway.json`, que [Railway está sustituyendo por Infrastructure as Code](https://docs.railway.com/infrastructure-as-code#iac-vs-config-as-code).

### 2. Crear el administrador en Railway

Una vez desplegado, usa una consola dentro del contenedor. Con Railway CLI:

```bash
railway login
railway link
railway ssh --service campus-quest-api
```

Adapta el nombre del servicio. Dentro de la sesión remota:

```bash
python -m backend.cli create-admin --email admin@tu-universidad.edu
```

Introduce la contraseña cuando se solicite. Si omitiste el pre-deploy inicial,
ejecuta antes `python -m backend.cli init`. Crea el admin una sola vez. No
necesitas dejar `ADMIN_PASSWORD` en variables permanentes ni ejecutar
`seed-demo` en producción.

`railway run` ejecuta comandos **localmente** con variables del proyecto; una
URL privada PostgreSQL puede no resolver desde tu equipo. Para estos comandos
usa [railway ssh](https://docs.railway.com/cli/ssh), que se ejecuta en el servicio.

### 3. Preparar Vercel

Importa el mismo repositorio y configura:

| Opción | Valor |
|---|---|
| Root Directory | `frontend` |
| Framework Preset | `Vite` |
| Node.js Version | `24.x` |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

Agrega estas variables al entorno Production:

```dotenv
VITE_DATA_MODE=api
VITE_API_BASE_URL=/api/v1
BACKEND_URL=https://tu-backend.up.railway.app
VITE_API_DOCS_URL=https://tu-backend.up.railway.app/docs
VITE_SITE_ORIGIN=https://tu-dashboard.vercel.app
```

`BACKEND_URL` es **el origen HTTPS**, sin `/api/v1`, rutas, query o credenciales.
Se usa solo dentro de la función de servidor. El navegador llama a `/api/v1`.
`VITE_API_DOCS_URL` permite abrir Swagger directamente en Railway.
`VITE_SITE_ORIGIN` es opcional para la tarjeta social; debe ser un origen HTTPS.

`frontend/vercel.json` reescribe `/api/v1/:path*` hacia `api/proxy.js`. La función
reenvía método, JSON, query, Cookie y Origin a Railway, y devuelve Set-Cookie y
el código HTTP original. Así el navegador guarda la cookie para **Vercel**,
con HttpOnly, Secure y SameSite=Lax. No depende de permitir cookies de terceros.
El proxy no acepta una URL de backend enviada por el visitante.

Vercel reconoce [funciones api/*.js en Vite](https://vercel.com/docs/frameworks/frontend/vite).
Consulta también [rewrites](https://vercel.com/docs/routing/rewrites) y
[runtime Node](https://vercel.com/docs/functions/runtimes/node-js).

### 4. Cerrar la conexión entre los servicios

Después de conocer el dominio definitivo Vercel, actualiza en Railway:

```dotenv
ALLOWED_ORIGINS=https://tu-dashboard.vercel.app
```

Si usas un dominio propio, añade ese origen exacto. Puedes separar varios con
comas. No añadas `/api/v1` a un origen. Las previews Vercel necesitan sus
orígenes explícitos y preferentemente un backend de pruebas; no abras la lista
con `*` ni uses sin control el backend real para previews.

Redeploy Railway si cambian sus variables. Redeploy Vercel si cambias variables
frontend o la URL del backend: las variables `VITE_*` se incorporan al build.

Verifica en la URL Vercel:

1. `/api/v1/health` devuelve `{ "status": "ok" }`.
2. Login administrativo abre el panel; recargar conserva la sesión.
3. Crear y editar una misión persiste tras recargar.
4. Archivar conserva el historial de los usuarios.
5. Cerrar sesión impide volver a consultar `/api/v1/usuarios` con esa cookie.

Android usará directamente `https://tu-backend.up.railway.app/api/v1/` con
Bearer cuando se implemente la capa remota. No necesita el proxy Vercel.

### Límites prácticos

PostgreSQL está soportado, pero requiere una prueba en Railway antes de usar
registros reales. Los tests locales se ejecutan sobre SQLite. Las funciones
Vercel limitan el tamaño de petición/respuesta: al crecer, paginar usuarios y
progreso. El proxy tiene timeout de 25 segundos y `maxDuration` de 30; devuelve
un error JSON cuando Railway no responde. No cachea respuestas personales.

No se ejecutó un deploy real en estos proveedores durante la preparación: las
cuentas, URLs y variables de destino se configuran siguiendo esta guía.

## Alternativa: Docker y un único dominio

Una imagen Docker compila React en una etapa Node y ejecuta FastAPI en la etapa
Python. FastAPI sirve `frontend/dist` y `/api/v1` desde la misma dirección.
Caddy puede proporcionar HTTPS y certificados automáticamente.

Esta estructura sigue el despliegue con [imagen propia recomendado por FastAPI](https://fastapi.tiangolo.com/deployment/docker/).
[Vite preview](https://vite.dev/guide/static-deploy) se reserva para revisar una
compilación local. El proceso de producción es Uvicorn, con un worker en el
MVP SQLite.

## Docker local

Desde la raíz:

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec app python -m backend.cli init
docker compose exec app python -m backend.cli create-admin --email admin@tu-universidad.edu
```

Abre <http://localhost:8000>. Para consultar el estado y los logs:

```bash
docker compose ps
docker compose logs --tail=100 app
curl http://localhost:8000/api/v1/health
```

La imagen ejecuta la aplicación con un usuario sin privilegios. El volumen
`campus_data` conserva `/app/data`; el puerto de FastAPI se expone únicamente
en `127.0.0.1` del servidor. No hay administrador ni registros ficticios al
arrancar: se crean mediante los comandos anteriores.

## Servidor con dominio y HTTPS

Necesitas un servidor Linux con Docker, DNS del dominio apuntando al servidor
y puertos 80/443 disponibles. Configura `.env`:

```dotenv
APP_ENV=production
COOKIE_SECURE=true
DATABASE_URL=sqlite:////app/data/campus_quest.db
SESSION_TTL_HOURS=24
DOMAIN=campus.tu-dominio.edu
SITE_ORIGIN=https://campus.tu-dominio.edu
ALLOWED_ORIGINS=https://campus.tu-dominio.edu
```

Después:

```bash
docker compose --profile production up -d --build
docker compose exec app python -m backend.cli init
docker compose exec app python -m backend.cli create-admin --email admin@tu-universidad.edu
```

La dirección será `https://campus.tu-dominio.edu`. Android, posteriormente,
usará `https://campus.tu-dominio.edu/api/v1/`.

`APP_ENV=production` exige `COOKIE_SECURE=true`. Abre el panel por **HTTPS**:
una cookie Secure no se enviará al acceder directamente al puerto HTTP 8000.
Caddy se comunica con FastAPI por la red privada de Compose; la lista explícita
de orígenes autoriza el dominio público para las mutaciones web.

Conserva los volúmenes `caddy_data` y `caddy_config` para mantener certificados.
No ejecutes `docker compose down -v` si quieres conservar datos: esa opción
borra los volúmenes.

## Otro hosting de contenedores

También puedes construir y ejecutar el Dockerfile en un servicio que soporte
contenedores. Configura:

1. Puerto de aplicación: `8000`.
2. HTTPS del proveedor delante de Uvicorn.
3. `APP_ENV=production`, `COOKIE_SECURE=true` y `ALLOWED_ORIGINS` con el origen
   público exacto, incluido `https://`.
4. Volumen persistente montado en `/app/data` si usas SQLite, o una BD PostgreSQL.
5. Variable de construcción `VITE_DATA_MODE=api`; URL web `/api/v1`.
6. Ejecutar `python -m backend.cli init` y crear el admin mediante una consola
   del servicio. No introducir contraseñas en argumentos de construcción.

Un filesystem efímero pierde SQLite al reemplazar el contenedor. No desplegar
varias réplicas con SQLite: usar una sola instancia o pasar a PostgreSQL.

## PostgreSQL

`psycopg` ya está incluido. Configura una instancia PostgreSQL del proveedor:

```dotenv
DATABASE_URL=postgresql+psycopg://usuario:contraseña@host:5432/campus_quest
```

Si el proveedor requiere TLS, conserva sus parámetros, por ejemplo
`?sslmode=require`. Usa credenciales como variables secretas del servidor.
Cambiar la URL no copia datos desde SQLite: antes de migrar una instalación
existente, planifica la exportación/importación y prueba que IDs, relaciones,
puntuación y secuencias se conservan.

`init` crea tablas e inserta el catálogo inicial. No representa un sistema de
migraciones de esquema. Antes de una segunda versión que cambie modelos,
incorporar Alembic, ejecutar las migraciones y comprobar una copia de BD.
Consulta [SQLAlchemy PostgreSQL](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg).

## Actualizar el servicio

Con una copia de seguridad y sin cambios de esquema pendientes:

```bash
git pull
docker compose --profile production up -d --build
docker compose logs --tail=100 app
```

Para una instalación local sin proxy, omite `--profile production`.
El volumen conserva usuarios, sesiones y progreso. No vuelvas a sembrar datos
ficticios ni recrees el administrador. `init` es idempotente para los registros
del catálogo que ya existen, pero no debe usarse para restaurar automáticamente
un catálogo editado en una instalación activa.

## Copias de seguridad SQLite

Usa la API de backup de SQLite, que crea una copia consistente mientras el
servicio está disponible:

```bash
docker compose exec app python -c "import sqlite3; src=sqlite3.connect('/app/data/campus_quest.db'); dst=sqlite3.connect('/app/data/backup.db'); src.backup(dst); dst.close(); src.close()"
docker compose cp app:/app/data/backup.db ./campus-quest-backup.db
```

Estos ejemplos suponen el nombre de archivo configurado para Docker. Si
cambiaste `DATABASE_URL`, adapta las rutas. La copia contiene datos personales
y hashes de sesión/contraseña: guárdala fuera de Git, con acceso restringido.
Prueba su restauración en una instancia aparte antes de depender de ella.
Para PostgreSQL usa backups administrados o `pg_dump` y un procedimiento de
restauración probado.

## Resolver problemas frecuentes

| Problema | Comprobación |
|---|---|
| Login no conserva la sesión | HTTPS + Secure coherentes; misma dirección web/API; cookie enviada |
| 403 al guardar con cookie | `ALLOWED_ORIGINS` contiene el origen exacto; no incluye rutas |
| Panel devuelve HTML como respuesta API | Usa `/api/v1`; revisa proxy Vite y servidor FastAPI |
| Panel sigue mostrando demo | `VITE_DATA_MODE` se aplica al compilar; reconstruye la imagen |
| Usuarios vacíos | `init` solo crea catálogo; crea admin y, para pruebas, `seed-demo` |
| Docker no conecta al daemon | Inicia Docker Engine; tener el CLI instalado no es suficiente |
| SQLite desaparece al redeploy | Asegura volumen persistente; evita `down -v` |
| Android no conecta a localhost | Usa `10.0.2.2` en el emulador o `adb reverse`; ver ANDROID.md |

En CORS con credenciales se requieren orígenes específicos, no `*`:
[documentación FastAPI](https://fastapi.tiangolo.com/tutorial/cors/).
