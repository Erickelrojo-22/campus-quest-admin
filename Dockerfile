FROM node:24-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_DATA_MODE=api
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_SITE_ORIGIN=
ENV VITE_DATA_MODE=$VITE_DATA_MODE VITE_API_BASE_URL=$VITE_API_BASE_URL VITE_SITE_ORIGIN=$VITE_SITE_ORIGIN
RUN npm run build

FROM python:3.13-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home campus && mkdir -p /app/data && chown campus:campus /app/data
COPY --chown=campus:campus backend/ ./backend/
COPY --from=frontend-build --chown=campus:campus /build/frontend/dist ./frontend/dist
ENV DATABASE_URL=sqlite:////app/data/campus_quest.db FRONTEND_DIST_DIR=/app/frontend/dist
USER campus
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
