"""
Partner Panel Backend - FastAPI Application

Mini App backend for NL International partners
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .config import settings
from .api import auth_router, credentials_router, channels_router, stats_router, traffic_stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Partner Panel Backend...")
    print(f"API available at http://{settings.api_host}:{settings.api_port}{settings.api_prefix}")

    # Initialize database tables
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))

        from shared.database.base import init_db
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization warning: {e}")

    yield

    # Shutdown
    print("Shutting down Partner Panel Backend...")


# Create FastAPI app
app = FastAPI(
    title="NL Partner Panel",
    description="""
    ## Partner Integration Panel for NL International

    Manage your Traffic Engine channels and track leads.

    ### Features:
    - **Authentication**: Telegram Mini App auth
    - **Credentials**: Manage Telegram accounts
    - **Channels**: Create and manage channels
    - **Statistics**: Track performance
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(credentials_router, prefix=settings.api_prefix)
app.include_router(channels_router, prefix=settings.api_prefix)
app.include_router(stats_router, prefix=settings.api_prefix)
app.include_router(traffic_stats_router, prefix=settings.api_prefix)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
    }


# API info
@app.get(settings.api_prefix)
async def api_info():
    """API information"""
    return {
        "name": "NL Partner Panel API",
        "version": "1.0.0",
        "endpoints": {
            "auth": f"{settings.api_prefix}/auth",
            "credentials": f"{settings.api_prefix}/credentials",
            "channels": f"{settings.api_prefix}/channels",
            "stats": f"{settings.api_prefix}/stats",
            "traffic": f"{settings.api_prefix}/traffic",
        },
        "docs": "/api/docs",
    }


# Serve Mini App frontend (when built)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        """Serve Mini App frontend"""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        """Serve frontend for all routes (SPA)"""
        file_path = os.path.join(FRONTEND_DIR, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    @app.get("/")
    async def no_frontend():
        """Placeholder when frontend not built"""
        return {
            "message": "Partner Panel API",
            "frontend": "not built yet",
            "docs": "/api/docs",
        }


def run():
    """Run the server"""
    import uvicorn
    uvicorn.run(
        "partner_panel.backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    run()
