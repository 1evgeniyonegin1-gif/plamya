"""
APEXFLOW Command Center — FastAPI Backend

Unified Mini App for content management, analytics, traffic monitoring, and AI Director.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys
from pathlib import Path

# Ensure project root is importable
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting APEXFLOW Command Center...")
    print(f"API at http://{settings.api_host}:{settings.api_port}{settings.api_prefix}")

    try:
        from shared.database.base import init_db
        await init_db()
        print("Database initialized")
    except Exception as e:
        print(f"Database init warning: {e}")

    yield
    print("Shutting down Command Center...")


app = FastAPI(
    title="APEXFLOW Command Center",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
from .api.auth import router as auth_router
from .api.posts import router as posts_router
from .api.analytics import router as analytics_router
from .api.traffic import router as traffic_router
from .api.director import router as director_router
from .api.diary import router as diary_router
from .api.schedule import router as schedule_router

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(posts_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
app.include_router(traffic_router, prefix=settings.api_prefix)
app.include_router(director_router, prefix=settings.api_prefix)
app.include_router(diary_router, prefix=settings.api_prefix)
app.include_router(schedule_router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


# Serve frontend SPA
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        file_path = os.path.join(FRONTEND_DIR, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    @app.get("/")
    async def no_frontend():
        return {"message": "APEXFLOW Command Center API", "docs": "/api/docs"}


def run():
    import uvicorn
    uvicorn.run(
        "content_manager_miniapp.backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    run()
