import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from pydantic import BaseModel, Field

from . import database
from .telemetry import setup_telemetry

telemetry = setup_telemetry()
logger = telemetry["logger"]


class ItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    status: str = Field(default="pending", pattern="^(pending|in_progress|done)$")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.init_db()
    logger.info("Application started and SQLite database initialized")
    yield


app = FastAPI(
    title="Proyecto Parcial 2 - Observabilidad & CI/CD",
    version="1.0.0",
    lifespan=lifespan,
)

FastAPIInstrumentor.instrument_app(app)
SQLite3Instrumentor().instrument()


@app.middleware("http")
async def metrics_and_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception(
            "Unhandled exception during HTTP request",
            extra={"extra_fields": {"endpoint": request.url.path, "method": request.method}},
        )
        raise
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        attrs = {
            "endpoint": request.url.path,
            "method": request.method,
            "statusCode": str(status_code),
        }
        telemetry["request_counter"].add(1, attrs)
        telemetry["latency_histogram"].record(duration_ms, attrs)
        if status_code >= 400:
            telemetry["error_counter"].add(1, attrs)

        logger.info(
            "HTTP request processed",
            extra={
                "extra_fields": {
                    "endpoint": request.url.path,
                    "method": request.method,
                    "statusCode": status_code,
                    "duration_ms": duration_ms,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            },
        )


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": os.getenv("OTEL_SERVICE_NAME", "proyecto2-app"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/api/items")
def get_items():
    return {"items": database.list_items()}


@app.post("/api/items", status_code=201)
def create_item(payload: ItemCreate):
    item = database.create_item(
        title=payload.title.strip(),
        description=payload.description.strip(),
        status=payload.status,
    )
    return item


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int):
    deleted = database.delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted": True, "id": item_id}


@app.get("/api/simulate-error")
def simulate_error():
    logger.error(
        "Simulated error endpoint triggered",
        extra={"extra_fields": {"endpoint": "/api/simulate-error", "statusCode": 500}},
    )
    return JSONResponse(status_code=500, content={"detail": "Simulated server error for observability"})


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
