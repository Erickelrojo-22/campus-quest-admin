# Verificación realizada

- Build React en modo `api`: correcto.
- Pruebas backend: **27 aprobadas** con SQLite.
- Pruebas frontend/adaptador/proxy: **14 aprobadas**.
- Smoke test HTTP real entre proxy Node y FastAPI: login, Cookie/Origin,
  listado de usuarios, edición, archivo, historial y revocación correctos.
- Configuraciones JSON y YAML: sintaxis válida.
- Endpoint de salud y servicio web compilado locales: HTTP 200.
- PostgreSQL Render real: tablas, catálogo de ocho misiones y ocho lugares,
  login administrativo, consulta autenticada, rechazo de Origin ajeno y
  revocación de sesión comprobados mediante la API ejecutada localmente.
- Acceso externo a PostgreSQL desactivado después de la inicialización.

Todavía no hay una API ni un dashboard publicados en Render/Vercel.
Se creó la base `campus-quest-db` gratuita de Render y el proyecto Vercel
`campus-quest-admin`, con raíz `frontend` y Fluid Compute activo. Render y
Vercel rechazaron la conexión al repositorio privado por falta de acceso
en sus integraciones GitHub. La sesión CLI de ambos proveedores está activa.
La base gratuita vence el **1 de noviembre de 2026, 00:47 UTC**.
El administrador y el catálogo ya existen; no se insertaron alumnos demo.
No se ejecutó el contenedor: el entorno local no dispone de Docker Engine
activo ni del plugin Compose. La revisión visual no se pudo realizar porque
no había un navegador conectado. React queda disponible en el puerto 5173
con la demostración local.

Las 41 pruebas automatizadas usan datos temporales y no modifican el
repositorio Android. La comprobación PostgreSQL adicional usó la base remota
recién creada: inició y revocó una sesión del administrador.
Starlette/TestClient muestra una advertencia de deprecación respecto a httpx; las 27 pruebas del servidor pasan.

Para repetir:

```bash
.venv/bin/python -m pytest tests -q
npm --prefix frontend test
VITE_DATA_MODE=api npm --prefix frontend run build
```

Después del deploy, seguir [las comprobaciones de conexión](DEPLOY.md#4-orígenes-definitivos-y-verificación).
