"""
FastAPI application and HTTP/WebSocket entrypoint.
Business logic and wiring live in src (screening, wiring).
"""
from fastapi import FastAPI

from apps.backend.routes import applications as applications_router
from apps.backend.routes import analysis as analysis_router
from apps.backend.routes import ws as ws_router


def create_app() -> FastAPI:
    app = FastAPI(title="Screening Backend", version="0.1.0")
    app.include_router(applications_router.router, prefix="/api")
    app.include_router(analysis_router.router, prefix="/api")
    app.include_router(ws_router.router, prefix="/api")
    return app


app = create_app()
