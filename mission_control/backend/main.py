"""
Mission Control — FastAPI application.

PLAMYA agent Command Center. No database required — reads/writes
plamya config files, STATUS.md, INBOX.md, COUNCIL.md, TASKS.md,
cron/jobs.json, and per-agent state files.

Run:
    python -m mission_control.backend.main
"""
import os
import sys
from contextlib import asynccontextmanager

# Fix: project has a `platform/` directory that shadows stdlib `platform` module.
# Remove project root from sys.path so uvicorn/starlette can import stdlib `platform`.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_platform_dir = os.path.join(_project_root, "platform")
if os.path.isdir(_platform_dir):
    sys.path = [p for p in sys.path if os.path.normcase(os.path.abspath(p)) != os.path.normcase(_project_root)]
    # Re-add project root AFTER stdlib paths so stdlib `platform` takes priority
    sys.path.append(_project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .services.file_watcher import FileWatcher
from .services.agents_service import AgentsService
from .services.errors_service import ErrorsService
from .services.event_bus import EventBus
from .services.file_monitor import FileMonitor

from .api.auth import router as auth_router
from .api.agents import router as agents_router
from .api.inbox import router as inbox_router
from .api.cron import router as cron_router
from .api.errors import router as errors_router
from .api.chat import router as chat_router
from .api.council import router as council_router
from .api.tasks import router as tasks_router
from .api.events import router as events_router
from .api.projects import router as projects_router
from .api.leads import router as leads_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared services on startup."""
    # Create singletons
    file_watcher = FileWatcher()
    agents_service = AgentsService(file_watcher, settings.plamya_dir)
    errors_service = ErrorsService(file_watcher, settings.plamya_dir)
    event_bus = EventBus()
    file_monitor = FileMonitor(event_bus, settings.plamya_dir)

    # Store on app.state so API endpoints can access them via request.app.state
    app.state.file_watcher = file_watcher
    app.state.agents_service = agents_service
    app.state.errors_service = errors_service
    app.state.event_bus = event_bus
    app.state.file_monitor = file_monitor

    # Start background file monitoring for SSE
    file_monitor.start()

    print(f"[Mission Control] Started on port {settings.api_port}")
    print(f"[Mission Control] PLAMYA dir: {settings.plamya_dir}")
    print("[Mission Control] SSE file monitor active (3s interval)")

    yield

    # Cleanup
    file_monitor.stop()
    print("[Mission Control] Shutting down.")


app = FastAPI(
    title="Mission Control",
    description="PLAMYA Agent Command Center",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers under /api/v1
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(agents_router, prefix=settings.api_prefix)
app.include_router(inbox_router, prefix=settings.api_prefix)
app.include_router(cron_router, prefix=settings.api_prefix)
app.include_router(errors_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(council_router, prefix=settings.api_prefix)
app.include_router(tasks_router, prefix=settings.api_prefix)
app.include_router(events_router, prefix=settings.api_prefix)
app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(leads_router, prefix=settings.api_prefix)


# ── Health check ─────────────────────────────────────

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return JSONResponse({"status": "ok", "service": "mission-control", "version": "2.0.0"})


# ── Serve frontend SPA ───────────────────────────────

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(_FRONTEND_DIR):
    # Serve static assets (js, css, images)
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(_FRONTEND_DIR, "assets")),
        name="static-assets",
    )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA index.html for any non-API route."""
        # Skip API routes
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)

        # Try to serve the exact file first (favicon.ico, etc.)
        file_path = os.path.join(_FRONTEND_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Fall back to index.html for SPA routing (no-cache to prevent stale assets)
        index_path = os.path.join(_FRONTEND_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(
                index_path,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

        return JSONResponse({"detail": "Frontend not built"}, status_code=404)


# ── Entry point ──────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "mission_control.backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        reload_dirs=[os.path.join(os.path.dirname(__file__), "..")],
    )
