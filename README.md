# Proyecto Parcial 2: CI/CD, Pruebas Automatizadas y Observabilidad

Implementación de una aplicación web (**FastAPI + SQLite + HTML/CSS/JS**) con pruebas automatizadas (**pytest** para backend y **Playwright** para frontend E2E), pipeline de **GitHub Actions** hacia **AWS EC2** con despliegue condicionado, e instrumentación **OpenTelemetry (OTLP)** hacia **OpenObserve**.

## Estructura del Proyecto

- `backend/app/` — API FastAPI, SQLite y telemetría OpenTelemetry (Logs, Métricas y Trazas).
- `frontend/` — Interfaz web servida por FastAPI.
- `tests/backend/` — Pruebas unitarias y de integración del backend con `pytest`.
- `tests/e2e/` — Pruebas de extremo a extremo (Frontend + Backend) con `Playwright`.
- `infra/otel-collector-config.yaml` — Configuración de OpenTelemetry Collector (métricas de host EC2: CPU, memoria, red, disco + reenvío OTLP a OpenObserve).
- `.github/workflows/ci-cd.yml` — Pipeline CI/CD con reporte de resultados a OpenObserve y despliegue SSH condicionado en EC2.
- `Dockerfile` y `docker-compose.yml` — Contenedores para despliegue en AWS EC2.

## Ejecución Local

### 1. Backend y pruebas con `pytest`
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt
pytest -v tests/backend
```

### 2. Pruebas E2E con `Playwright`
```bash
cd tests/e2e
npm install
npx playwright install chromium
npx playwright test
```

### 3. Levantar la aplicación manualmente
```bash
uvicorn backend.app.main:app --reload
```
Abrir `http://127.0.0.1:8000`.

## Configuración de GitHub Actions Secrets

En **Settings > Secrets and variables > Actions** del repositorio en GitHub:

- `OPENOBSERVE_URL`: URL base de OpenObserve (ej. `https://openobserve.midominio.com:5080`)
- `OPENOBSERVE_TOKEN`: Credenciales en Base64 (`usuario:password`) para `Authorization: Basic`
- `EC2_HOST`: IP pública o DNS de la instancia AWS EC2
- `EC2_USER`: Usuario SSH (ej. `ubuntu` o `ec2-user`)
- `EC2_SSH_KEY`: Llave privada SSH (`.pem`)
- `EC2_APP_DIR`: Ruta del repositorio en EC2 (ej. `/home/ubuntu/proyecto-parcial2-cicd`)

## Despliegue en AWS EC2

1. Clonar el repositorio en la instancia EC2 y crear el archivo `.env` basado en `.env.example`.
2. Ejecutar `docker compose up -d --build`.
3. En OpenObserve se recibirán:
   - **Stream `ci_cd_events`**: Resultados de pruebas CI y eventos de despliegue.
   - **Logs, Métricas y Trazas (`default`)**: Telemetría OTLP de la aplicación FastAPI + SQLite y métricas de infraestructura del servidor EC2 vía `hostmetrics`.
