from .auth import router as auth_router
from .posts import router as posts_router
from .analytics import router as analytics_router
from .traffic import router as traffic_router
from .director import router as director_router
from .diary import router as diary_router
from .schedule import router as schedule_router

__all__ = [
    "auth_router",
    "posts_router",
    "analytics_router",
    "traffic_router",
    "director_router",
    "diary_router",
    "schedule_router",
]
