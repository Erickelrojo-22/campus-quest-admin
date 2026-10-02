# Campus Quest · Panel web y API

MVP para administrar Campus Quest: perfiles de usuarios, puntos, niveles,
misiones, lugares del campus, insignias e informes CSV. El panel usa **React 19,
Vite y Tailwind CSS**; el servidor usa **FastAPI y SQLAlchemy**.

El frontend está dentro de `frontend/`. El backend está fuera de esa carpeta,
en `backend/`. El despliegue previsto es **backend en Railway y frontend en Vercel**.
Un proxy en Vercel conecta `/api/v1` con Railway y conserva la sesión web
en el mismo origen. También se incluye Docker para ejecutar todo junto.
Android podrá consumir directamente la API de Railway en la siguiente etapa.

## Qué funciona

- Resumen calculado desde usuarios y progreso, ranking y actividad semanal.
- Búsqueda y filtros de usuarios, consulta de perfiles e historial de insignias.
- Crear, editar, archivar y reactivar misiones. Archivar conserva el historial.
- Crear y editar puntos del campus, coordenadas en el mapa y códigos QR únicos.
- Reportes por periodo y exportación CSV de usuarios y completaciones.
- Login administrativo real, sesión HttpOnly y permisos verificados en servidor.
- API de progreso: valida el QR, registra la misión y otorga puntos una sola vez,
  incluso con solicitudes simultáneas o reintentos.
- SQLite persistente para el MVP; configuración alternativa para PostgreSQL.
- Vista de demostración independiente, con registros ficticios **en memoria**.

La app Android existente sigue usando Room local: **todavía no se sincroniza**
con este servidor. No se modificó ese repositorio. El catálogo de ocho lugares,
ocho misiones y el mapa se tomaron de
`/home/elkindev/AndroidStudioProjects/Gamequest`. Los usuarios y el progreso de
prueba son ficticios. Cursos, premios canjeables y registro público no forman
parte de este MVP.

## Estructura

```text
campus-quest-admin/
├── frontend/
│   ├── src/pages/             # Resumen, perfiles, misiones, mapa e informes
│   ├── src/services/          # Adaptadores FastAPI y demo
│   ├── src/data/              # Catálogo Android y usuarios ficticios
│   ├── public/                # Mapa, fuente de marca y tarjeta social
│   ├── tests/                 # Contrato HTTP, demo y exportación
│   ├── api/proxy.js          # Proxy Vercel → Railway
│   ├── vercel.json
│   ├── .env.example
│   └── package.json
├── backend/
│   ├── app.py                # API, autorización y frontend compilado
│   ├── models.py             # Tablas SQLAlchemy
│   ├── schemas.py            # Validación de entradas y JSON público
│   ├── security.py           # Contraseñas, sesiones y permisos
│   ├── config.py
│   ├── cli.py                # Inicialización y creación de administrador
│   └── catalog.json          # Catálogo original Android
├── tests/                    # Integración real de API y concurrencia
├── docs/                     # Arquitectura, contrato, deploy y Android
├── deploy/Caddyfile          # HTTPS automático para producción
├── Dockerfile.backend        # Solo FastAPI para Railway
├── Dockerfile                # Web + API para Docker local
├── compose.yaml
├── requirements.txt
└── .env.example
```

## 1. Probar solo el dashboard

Requiere Node **22.13 o superior**; se recomienda Node 24 LTS.

```bash
cd frontend
npm ci
npm run dev
```

Abre la dirección que Vite indique, normalmente <http://localhost:5173>.
Sin `.env`, el panel abre en modo demo. Puedes explorar perfiles, crear misiones,
archivarlas y cambiar lugares. **Recargar la página restablece la demo**.
No se necesita contraseña ni servidor Python para esta vista.

## 2. Ejecutar frontend + backend real

Requiere Python **3.13 o superior**. Todos los comandos Python se ejecutan desde
la raíz del repositorio.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
set -a
source .env
set +a
python -m backend.cli init
python -m backend.cli create-admin --email admin@tu-universidad.edu
```

`create-admin` solicita una contraseña de 8 a 256 caracteres, que se guarda
como hash. No hay credenciales administrativas predeterminadas. `init` crea
las tablas y carga el catálogo de Android; no crea alumnos ni un admin.

Opcional, solo para probar perfiles e informes con datos ficticios:

```bash
python -m backend.cli seed-demo
```

Inicia la API en la primera terminal:

```bash
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

En otra terminal, desde la raíz:

```bash
cp frontend/.env.example frontend/.env
npm --prefix frontend ci
npm --prefix frontend run dev
```

Abre <http://localhost:5173> e inicia sesión con el administrador que creaste.
Ahora los cambios se guardan en SQLite. Vite reenvía `/api` a FastAPI:
**no tienes que introducir una URL diferente en cada petición**.

- Salud: <http://localhost:8000/api/v1/health>
- API interactiva: <http://localhost:8000/docs>
- Contrato OpenAPI: <http://localhost:8000/openapi.json>

Si quieres volver a la vista demo, cambia `VITE_DATA_MODE=demo` en
`frontend/.env` y reinicia Vite. Un fallo del servidor en modo API muestra el
error; nunca cambia silenciosamente a registros ficticios.

## 3. Ejecutar la versión compilada

Con el entorno Python activado y las variables `.env` cargadas:

```bash
VITE_DATA_MODE=api npm --prefix frontend run build
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Abre <http://localhost:8000>. FastAPI sirve el dashboard y `/api/v1` en el mismo
origen. Esto reproduce la arquitectura de despliegue. `vite preview` sirve
solo para revisión local y no es el servidor de producción.

## 4. Railway + Vercel: despliegue recomendado

Sigue [la guía completa de despliegue](docs/DEPLOY.md#railway--vercel).

- **Railway**: raíz del repositorio, `Dockerfile.backend`, PostgreSQL,
  `APP_ENV=production`, `COOKIE_SECURE=true` y `ALLOWED_ORIGINS` con la URL Vercel.
- **Vercel**: Root Directory `frontend`, framework Vite, build `npm run build`,
  salida `dist` y Node 24.
- **Variables Vercel**: `VITE_DATA_MODE=api`, `VITE_API_BASE_URL=/api/v1`,
  `BACKEND_URL=https://tu-backend.up.railway.app` y
  `VITE_API_DOCS_URL=https://tu-backend.up.railway.app/docs`.

El proxy incluido reenvía las cookies y el Origin del navegador. No necesitas
cambiar a cookies entre dominios ni exponer una credencial del backend en React.

## 5. Docker: todo en un servicio

Necesitas Docker Engine en ejecución y Docker Compose.

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec app python -m backend.cli init
docker compose exec app python -m backend.cli create-admin --email admin@tu-universidad.edu
```

Abre <http://localhost:8000>. El frontend se compila automáticamente en modo
API durante la construcción de la imagen. SQLite vive en el volumen
`campus_data`; reiniciar o reconstruir el contenedor conserva los datos.

Opcional para pruebas:

```bash
docker compose exec app python -m backend.cli seed-demo
```

Este comando carga registros ficticios; omítelo en tu despliegue real.
Consulta los pasos de dominio, HTTPS, PostgreSQL, copias de seguridad y
actualizaciones en [docs/DEPLOY.md](docs/DEPLOY.md).

## Configuración

| Variable | Dónde | Uso |
|---|---|---|
| `DATABASE_URL` | Backend | SQLite o `postgresql+psycopg://...` |
| `APP_ENV` | Backend | `development` o `production` |
| `COOKIE_SECURE` | Backend | `false` en HTTP local; `true` con HTTPS |
| `ALLOWED_ORIGINS` | Backend | Orígenes autorizados, separados por comas |
| `SESSION_TTL_HOURS` | Backend | Duración de la sesión, 24 horas por defecto |
| `FRONTEND_DIST_DIR` | Backend | Carpeta compilada que FastAPI sirve |
| `VITE_DATA_MODE` | Frontend, al compilar | `api` o `demo` |
| `VITE_API_BASE_URL` | Frontend, al compilar | `/api/v1` para el mismo origen |
| `API_PROXY_TARGET` | Vite, desarrollo | Servidor al que reenvía `/api` |
| `BACKEND_URL` | Función Vercel | Origen HTTPS de Railway, sin `/api/v1` |
| `VITE_API_DOCS_URL` | Frontend | Enlace público a Swagger en Railway |
| `VITE_SITE_ORIGIN` | Frontend, al compilar | Origen HTTPS de la tarjeta social |
| `DOMAIN` | Compose, perfil producción | Dominio público de Caddy |
| `SITE_ORIGIN` | Compose, al compilar | Se pasa a `VITE_SITE_ORIGIN` |

Los archivos `.env`, las bases SQLite y `.venv/` se excluyen de Git. Nunca
introduzcas contraseñas, claves privadas o credenciales de BD en `VITE_*`:
esas variables forman parte del JavaScript público del navegador.

## Documentación y verificación

- [Arquitectura y decisiones](docs/ARCHITECTURE.md)
- [Contrato API y ejemplos](docs/API.md)
- [Despliegue y mantenimiento](docs/DEPLOY.md)
- [Integración Android, próxima etapa](docs/ANDROID.md)
- [Verificación realizada y pendientes](docs/VALIDATION.md)

```bash
.venv/bin/python -m pytest tests -q
npm --prefix frontend test
npm --prefix frontend run build
```

Las pruebas del servidor cubren sesiones, permisos, privacidad, QR únicos,
archivo, historial y completaciones concurrentes. Las del frontend verifican
su adaptador HTTP y que los errores remotos no se sustituyan por datos demo.
PostgreSQL y el despliegue HTTPS deben verificarse en el entorno de destino.
