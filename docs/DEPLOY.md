# Despliegue y mantenimiento

## Render + Vercel: MVP gratuito

Render ejecuta FastAPI con Python nativo y PostgreSQL; Vercel compila React y
sirve el proxy de `/api/v1`. Las direcciones `tu-backend.onrender.com` y
`tu-dashboard.vercel.app` de esta guía son ejemplos; usa las URLs verificadas
de tus servicios al configurar las variables.

```mermaid
flowchart LR
    N[Navegador] -->|mismo origen /api/v1| V[Vercel: React + proxy]
    V -->|HTTPS, Cookie y Origin| R[Render: FastAPI Python]
    R -->|red interna| P[(PostgreSQL Render)]
    A[Android · próxima etapa] -.->|HTTPS + Bearer| R
```

### Estado de la preparación actual

La sesión CLI de Render y Vercel está iniciada. Se creó PostgreSQL
`campus-quest-db` (`dpg-davfu9id0e5s73frhh8g-a`, Virginia), se inicializó el
catálogo y se creó un administrador. La BD gratuita vence el **1 de noviembre
de 2026 a las 00:47 UTC**. Su acceso externo está desactivado; para tareas
locales posteriores hay que autorizar temporalmente la IP otra vez.

El proyecto Vercel `campus-quest-admin` tiene Root Directory `frontend`, Node
24 y Fluid Compute activo; tiene asignado `campus-quest-admin.vercel.app`,
pero aún no hay un deployment publicado. Render rechazó crear el backend
porque no puede leer el repositorio privado. Vercel también rechazó conectar
ese repositorio para despliegues automáticos. El propietario debe autorizar
`Erickelrojo-22/campus-quest-admin` para ambas aplicaciones en
[instalaciones GitHub](https://github.com/settings/installations).
Iniciar sesión en la CLI no concede por sí solo ese acceso al código.

Las URLs de backend de los pasos siguientes siguen siendo ejemplos hasta
crear el servicio. No repitas `create-admin` con el mismo correo: ese comando
rechaza una cuenta existente y no cambia su contraseña. Consulta
[la verificación actual](VALIDATION.md) antes de repetir la inicialización.

### 1. PostgreSQL y servicio Python en Render

1. Crea PostgreSQL en Render y un Web Service desde el repositorio. Mantén
   ambos en la misma región para usar la URL interna de la BD.
2. Deja Root Directory vacío, equivalente a la raíz. Selecciona **Python 3**
   como runtime: el repositorio contiene un `Dockerfile`, pero este despliegue
   usa Python nativo. Confirma el runtime antes de crear el servicio.
3. Configura estos valores:

   | Opción | Valor |
   |---|---|
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn backend.app:app --host 0.0.0.0 --port $PORT --workers 1` |
   | Health Check Path | `/api/v1/health` |
   | Pre-deploy Command, plan Free | Vacío |

   `PORT` lo proporciona Render. Las dependencias y el módulo `backend` están
   en la raíz; no cambies Root Directory a `frontend` ni a `backend`.
4. Agrega las variables del servicio:

   ```dotenv
   PYTHON_VERSION=3.13.16
   APP_ENV=production
   COOKIE_SECURE=true
   SESSION_TTL_HOURS=24
   ALLOWED_ORIGINS=https://tu-dashboard.vercel.app
   ```

   Configura `DATABASE_URL` por separado como secreto, copiando la **Internal
   Database URL** desde PostgreSQL. No la publiques en Git, logs ni variables
   `VITE_*`. El backend admite `postgresql://` y `postgresql+psycopg://`.
5. Despliega y verifica `https://tu-backend.onrender.com/api/v1/health` y
   `https://tu-backend.onrender.com/docs`. La raíz del backend puede devolver
   404 porque el dashboard se sirve desde Vercel.

La configuración sigue las guías de [FastAPI en Render](https://render.com/docs/deploy-fastapi)
y [versiones Python](https://render.com/docs/python-version). El pin
[Python 3.13.16](https://www.python.org/downloads/release/python-31316/) fue
publicado el 30 de septiembre de 2026. Revisa su actualización al mantener
el servicio; Render permite fijar versiones publicadas mediante `PYTHON_VERSION`.

### 2. Inicializar catálogo y administrador sin SSH

Render Free no ofrece [SSH ni Shell del dashboard](https://render.com/docs/ssh).
El [pre-deploy está disponible en planes pagados](https://render.com/docs/deploys#pre-deploy-command).
Por eso el catálogo y el administrador se crean desde tu equipo, conectando
los comandos existentes a PostgreSQL remoto. El inicio de FastAPI solo crea
tablas; no crea cuentas administrativas ni usuarios demo.

En PostgreSQL, abre **Info → Networking** y autoriza temporalmente tu IP
pública exacta como `/32`. Después copia su **External Database URL**. Usa
el hostname completo y SSL: añade `?sslmode=require`, o `&sslmode=require` si
la URL ya contiene parámetros. No utilices la URL interna desde tu equipo.
[Conexión externa, TLS y restricciones IP de Render](https://render.com/docs/postgresql-creating-connecting#external-connections).

Desde la raíz del repositorio, con Python y las dependencias instaladas:

```bash
source .venv/bin/activate
read -r -s -p 'URL externa PostgreSQL con sslmode=require: ' CQ_RENDER_DATABASE_URL
printf '\n'
DATABASE_URL="$CQ_RENDER_DATABASE_URL" APP_ENV=production COOKIE_SECURE=true python -m backend.cli init
DATABASE_URL="$CQ_RENDER_DATABASE_URL" APP_ENV=production COOKIE_SECURE=true python -m backend.cli create-admin --email admin@tu-universidad.edu
unset CQ_RENDER_DATABASE_URL
```

El primer prompt oculta la URL y evita escribirla en el historial de comandos;
el segundo solicita la contraseña del admin con `getpass`. No necesitas
guardar `ADMIN_PASSWORD` en Render ni construir un endpoint público de alta.
Retira la autorización IP temporal al terminar, dejando desactivado el acceso
externo si no lo necesitas. El backend mantiene acceso por la URL interna.
`init` conserva los IDs existentes del catálogo; no lo uses como migración de
esquema ni para recuperar registros editados.

### 3. Dashboard y proxy en Vercel

Importa el repositorio en Vercel con Root Directory `frontend`, preset Vite,
Node `24.x`, Install Command `npm ci`, Build Command `npm run build` y Output
Directory `dist`. Activa **Fluid Compute**: el proxy limita cada espera HTTP
a 90 segundos y `frontend/vercel.json` establece `maxDuration=120`.
La configuración actual con Fluid admite ese valor en Hobby;
[duración de funciones Vercel](https://vercel.com/docs/functions/configuring-functions/duration)
y [activación de Fluid Compute](https://vercel.com/docs/fluid-compute).

Agrega al entorno Production:

```dotenv
VITE_DATA_MODE=api
VITE_API_BASE_URL=/api/v1
BACKEND_URL=https://tu-backend.onrender.com
VITE_API_DOCS_URL=https://tu-backend.onrender.com/docs
VITE_SITE_ORIGIN=https://tu-dashboard.vercel.app
```

`BACKEND_URL` pertenece a la función de servidor y contiene únicamente el
origen HTTPS del backend, sin `/api/v1` ni credenciales. La función conserva
Cookie, Origin y Set-Cookie; el navegador guarda la sesión HttpOnly, Secure
y SameSite=Lax en el dominio Vercel. Los secretos PostgreSQL solo pertenecen
al backend. `VITE_*` se incorpora al JavaScript público durante el build.

### 4. Orígenes definitivos y verificación

Cuando Vercel entregue su URL estable, actualiza `ALLOWED_ORIGINS` en Render
con ese origen HTTPS **exacto**, sin rutas. Si añades un dominio propio, usa
una lista explícita separada por comas. Las previews requieren autorizar su
origen por separado, preferiblemente contra una BD de pruebas; no uses `*`.
Redeploy el servicio si cambian sus variables. Redeploy Vercel si cambian las
variables frontend o `BACKEND_URL`.

Comprueba desde el dominio Vercel:

1. `/api/v1/health` devuelve `{ "status": "ok" }`.
2. Login, recarga y consulta de perfiles conservan la sesión.
3. Crear/editar/archivar una misión persiste y conserva el historial.
4. Logout revoca la sesión e impide consultar `/api/v1/usuarios`.
5. La BD conserva los cambios después de redeploy Render.

Android se conectará directamente a `https://tu-backend.onrender.com/api/v1/`
con Bearer cuando se implemente su integración; no necesita el proxy Vercel.

### Límites del MVP gratuito

La API Free se pausa tras 15 minutos sin tráfico y tarda aproximadamente un
minuto en despertar. El filesystem es efímero: usa PostgreSQL, no SQLite
local. PostgreSQL Free expira 30 días después de crearse y no incluye backups
administrados. Antes del vencimiento, exporta/restaura los datos o cambia a
un plan con continuidad. [Límites oficiales Render Free](https://render.com/docs/free).

El timeout de 90 segundos del proxy permite esperar el arranque habitual,
pero no garantiza que cada reactivación termine a tiempo. Ante un error,
consulta el healthcheck y reintenta; el dashboard no sustituye el fallo por
datos ficticios. Las pruebas locales SQLite no acreditan un deploy remoto. La base PostgreSQL
ya se comprobó usando la API local; falta verificar el servicio desplegado
y el proxy Vercel en sus dominios públicos.

## Railway + Vercel: alternativa

Railway puede ejecutar el mismo backend y PostgreSQL; Vercel conserva el
dashboard y el proxy. Esta alternativa usa `Dockerfile.backend` desde la
raíz del repositorio.

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
progreso. El proxy tiene timeout de 90 segundos y `maxDuration` de 120 con
Fluid Compute activo; devuelve
un error JSON cuando Railway no responde. No cachea respuestas personales.

Las URLs de esta sección son ejemplos de configuración, no direcciones finales
verificadas. Registra el despliegue y sus comprobaciones al completar la publicación.

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
| Render Free pierde SQLite | Usa PostgreSQL: el filesystem del Web Service es efímero |
| Primera petición a Render tarda o devuelve 502 | API pausada tras inactividad; espera reactivación y revisa healthcheck |
| Inicialización local no conecta a Render PostgreSQL | URL externa, hostname completo, `sslmode=require` e IP autorizada temporalmente |
| Render intenta construir Docker | Cambia runtime del Web Service a Python 3 y deja Root Directory en raíz |
| Vercel corta el proxy antes de 120 s | Confirma Fluid Compute y configuración `maxDuration` del proyecto |
| Android no conecta a localhost | Usa `10.0.2.2` en el emulador o `adb reverse`; ver ANDROID.md |

En CORS con credenciales se requieren orígenes específicos, no `*`:
[documentación FastAPI](https://fastapi.tiangolo.com/tutorial/cors/).
