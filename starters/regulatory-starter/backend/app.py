"""Working inherited application foundation; regulatory endpoints are not implemented."""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from pydantic import Field
from . import auth
from .db import engine
from .domain import StrictModel, RuleError
from .security import guard, origins


@asynccontextmanager
async def lifespan(app):
    auth.development_login()  # Validates APP_ENV; no demo-login route or seed exists.
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    expected = ScriptDirectory.from_config(config).get_current_head()
    with engine().connect() as db:
        if db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() != expected:
            raise RuntimeError("Run migrations explicitly before starting.")
    yield


app = FastAPI(title="Regulatory Workspace Foundation", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "Authorization"],
)
app.middleware("http")(guard)


@app.exception_handler(RequestValidationError)
async def invalid(request, exc):
    # Avoid reflecting credentials or arbitrary input into validation responses.
    return JSONResponse({"detail": "Invalid request fields. Check the form."}, status_code=422)


@app.exception_handler(RuleError)
async def rule_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409)


class Login(StrictModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


def identity(p):
    return {
        "user_id": p.user_id,
        "store": {"id": p.store_id, "name": p.store_name, "timezone": p.timezone},
        "role": p.role,
        "permissions": sorted(auth.PERMISSIONS[p.role]),
    }


@app.get("/api/health")
def health():
    return {"ok": True, "foundation_only": True, "regulatory_sources_connected": False}


@app.post("/api/auth/login")
def login(body: Login):
    p, token, csrf = auth.login(body.username, body.password)
    response = JSONResponse({**identity(p), "csrf": csrf})
    secure = os.getenv("APP_ENV", "production") == "production"
    response.set_cookie(
        "rp_session",
        token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=43200,
        path="/api",
    )
    response.set_cookie(
        "rp_csrf", csrf, httponly=False, secure=secure, samesite="strict", max_age=43200, path="/"
    )
    return response


@app.get("/api/auth/me")
def me():
    return identity(auth.current())


@app.post("/api/auth/logout")
def logout(request: Request):
    bearer = request.headers.get("authorization", "")
    auth.revoke(
        bearer[7:] if bearer.startswith("Bearer ") else request.cookies.get("rp_session", "")
    )
    response = JSONResponse({"signed_out": True})
    response.delete_cookie("rp_session", path="/api")
    response.delete_cookie("rp_csrf", path="/")
    return response


DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if (DIST / "index.html").is_file() and (DIST / "assets").is_dir():
    # Mount only after API registration; incomplete builds never break imports.
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
