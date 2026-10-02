# Verificación realizada

- Build React en modo `api`: correcto.
- Pruebas backend: **27 aprobadas** con SQLite.
- Pruebas frontend/adaptador/proxy: **14 aprobadas**.
- Smoke test HTTP real entre proxy Node y FastAPI: login, Cookie/Origin,
  listado de usuarios, edición, archivo, historial y revocación correctos.
- Configuraciones JSON y YAML: sintaxis válida.
- Endpoint de salud y servicio web compilado: HTTP 200.

No se ejecutó un despliegue en Railway/Vercel ni una instancia PostgreSQL.
No se ejecutó el contenedor: el entorno local no dispone de Docker Engine
activo ni del plugin Compose. La revisión visual no se pudo realizar porque
no había un navegador conectado. React queda disponible en el puerto 5173
con la demostración local.

Los tests usan datos temporales; no modifican una BD real ni el repositorio
Android. Starlette/TestClient muestra una advertencia de deprecación respecto
a httpx; las 27 pruebas del servidor pasan.

Para repetir:

```bash
.venv/bin/python -m pytest tests -q
npm --prefix frontend test
VITE_DATA_MODE=api npm --prefix frontend run build
```

Después del deploy, seguir [las comprobaciones de conexión](DEPLOY.md#4-cerrar-la-conexión-entre-los-servicios).
