# Verificación realizada

- Build React en modo `api`: correcto.
- Pruebas backend: **33 aprobadas** con SQLite.
- Pruebas frontend/adaptador/proxy: **14 aprobadas**.
- Smoke test HTTP real entre proxy Node y FastAPI: login, Cookie/Origin,
  listado de usuarios, edición, archivo, historial y revocación correctos.
- Configuraciones JSON y YAML: sintaxis válida.
- Endpoint de salud y servicio web compilado locales: HTTP 200.
- PostgreSQL Render real: tablas, catálogo de ocho misiones y ocho lugares,
  login administrativo, consulta autenticada, rechazo de Origin ajeno y
  revocación de sesión comprobados mediante la API ejecutada localmente.
- Acceso externo a PostgreSQL desactivado después de la inicialización.

El 4 de octubre de 2026 se verificó el despliegue público: healthcheck HTTP
200, login administrativo, listado de usuarios, puntos, misiones y progreso,
y revocación de la sesión, pasando por Vercel hacia Render. Inventario en ese
momento: 2 administradores, 8 puntos, 8 misiones, 0 completaciones.
La base PostgreSQL gratuita vence el **1 de noviembre de 2026, 00:47 UTC**,
según la información actual del servicio Render.

No se ejecutó el contenedor: el entorno local no dispone de Docker Engine
activo ni del plugin Compose. La revisión visual no se pudo realizar porque
no había un navegador conectado. React queda disponible en el puerto 5173
con la demostración local.

Las 47 pruebas automatizadas usan datos temporales y no modifican el
repositorio Android. La comprobación PostgreSQL adicional usó la base remota
recién creada: inició y revocó una sesión del administrador.
Starlette/TestClient muestra una advertencia de deprecación respecto a httpx; las 33 pruebas del servidor pasan.

Para repetir:

```bash
.venv/bin/python -m pytest tests -q
npm --prefix frontend test
VITE_DATA_MODE=api npm --prefix frontend run build
```

Después del deploy, seguir [las comprobaciones de conexión](DEPLOY.md#4-orígenes-definitivos-y-verificación).
