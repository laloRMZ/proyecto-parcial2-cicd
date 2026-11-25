import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from pydantic import BaseModel, Field

from . import database
from .telemetry import setup_telemetry

telemetry = setup_telemetry()
logger = telemetry["logger"]

TOKEN_TTL_SECONDS = 86400


def _get_secret_key() -> str:
    return os.getenv("APP_SECRET_KEY", "proyecto2-dev-secret-change-in-prod")


def create_access_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    sig = hmac.new(_get_secret_key().encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def decode_access_token(token: str) -> dict:
    try:
        payload_b64, sig = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token format") from exc

    expected_sig = hmac.new(_get_secret_key().encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8"))
    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired")
    return payload


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    user = database.get_user_by_id(int(payload["sub"]))
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=60)
    password: str = Field(..., min_length=1, max_length=128)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=60)
    email: str = Field(..., min_length=5, max_length=120)
    full_name: str = Field(..., min_length=2, max_length=120)
    role: str = Field(default="user", pattern="^(admin|user|viewer)$")
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdate(BaseModel):
    email: Optional[str] = Field(default=None, min_length=5, max_length=120)
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    role: Optional[str] = Field(default=None, pattern="^(admin|user|viewer)$")
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.init_db()
    logger.info("Application started and SQLite users database initialized")
    yield


app = FastAPI(
    title="Proyecto Parcial 2 - Login, CRUD Users & Observabilidad",
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


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    user = database.authenticate_user(payload.username.strip(), payload.password)
    if not user:
        logger.warning(
            "Failed login attempt",
            extra={"extra_fields": {"username": payload.username.strip(), "statusCode": 401}},
        )
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/api/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


@app.get("/api/users")
def list_users(current_user: dict = Depends(get_current_user)):
    return {"users": database.list_users()}


@app.post("/api/users", status_code=201)
def create_user(payload: UserCreate, current_user: dict = Depends(get_current_user)):
    try:
        return database.create_user(
            username=payload.username.strip(),
            email=payload.email.strip(),
            full_name=payload.full_name.strip(),
            role=payload.role,
            password=payload.password,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="El usuario o correo ya existe") from exc


@app.put("/api/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate, current_user: dict = Depends(get_current_user)):
    try:
        updated = database.update_user(
            user_id=user_id,
            email=payload.email.strip() if payload.email is not None else None,
            full_name=payload.full_name.strip() if payload.full_name is not None else None,
            role=payload.role,
            is_active=payload.is_active,
            password=payload.password,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="El correo ya está en uso") from exc

    if not updated:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return updated


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, current_user: dict = Depends(get_current_user)):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario en sesión")
    deleted = database.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"deleted": True, "id": user_id}


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
