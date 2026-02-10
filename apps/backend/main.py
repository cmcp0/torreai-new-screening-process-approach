"""
FastAPI application and HTTP/WebSocket entrypoint.
Business logic and wiring live in src (screening, wiring).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.backend.routes import applications as applications_router
from apps.backend.routes import analysis as analysis_router
from apps.backend.routes import ws as ws_router
from src.config import Settings


def create_app() -> FastAPI:
    settings = Settings()
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if not origins:
        origins = ["http://localhost:5173"]

    app = FastAPI(title="Screening Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(applications_router.router, prefix="/api")
    app.include_router(analysis_router.router, prefix="/api")
    app.include_router(ws_router.router, prefix="/api")
    return app


app = create_app()
