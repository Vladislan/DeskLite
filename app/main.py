# app/main.py
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    health,
    auth,
    users,
    tickets,
    comments,
    admin,
    questions,
    operator_feedback,   # 👈 додали
)

from app.core.config import settings
from app.core.logging import setup_logging, RequestIdMiddleware

setup_logging(settings.log_level)

app = FastAPI(
    title="Helpdesk Lite",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

# ==== Middlewares ====
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIdMiddleware)

# ==== API під /api ====
app.include_router(health.router,    prefix="/api",        tags=["health"])
app.include_router(auth.router,      prefix="/api/auth",   tags=["auth"])
app.include_router(users.router,     prefix="/api/users",  tags=["users"])
app.include_router(tickets.router,   prefix="/api/tickets", tags=["tickets"])
app.include_router(comments.router,  prefix="/api/tickets", tags=["comments"])
app.include_router(admin.router,     prefix="/api/admin",  tags=["admin"])
app.include_router(operator_feedback.router, prefix="/api/operator", tags=["operator"])



# ВАЖЛИВО: підключаємо questions-роутер!
# У нього вже prefix="/questions", тому тут даємо prefix="/api"
app.include_router(questions.router, prefix="/api")

# ==== Статика (SPA) ====
BASE_DIR = Path(__file__).resolve().parents[1]
_ui_env = os.getenv("UI_DIST_DIR")
_ui_conf = settings.ui_dist_dir
UI_DIST = Path(_ui_conf or _ui_env or (BASE_DIR / "front" / "dist"))

if UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="ui")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        index = UI_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"detail": "UI build not found"}, 404
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"status": "ok", "ui": "not built", "build_at": str(UI_DIST)}
