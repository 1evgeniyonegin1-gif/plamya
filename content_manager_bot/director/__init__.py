"""
AI Content Director — продюсер каналов.

7 модулей:
- PerformanceAnalyzer: Contextual Bandit (LinUCB) + pre-publish scoring
- EditorialPlanner: AI недельный контент-план
- ChannelMemory: Structured memory (Mem0/A.U.D.N.)
- SelfReviewer: AI самоанализ каждые 10 постов
- ReflectionEngine: Обучение на правках/отклонениях
- CompetitorAnalyzer: Анализ конкурентов через Telethon
- TrendDetector: Trending темы (чистый Python)
"""

from content_manager_bot.director.performance_analyzer import (
    PerformanceAnalyzer,
    get_performance_analyzer,
)
from content_manager_bot.director.editorial_planner import (
    EditorialPlanner,
    get_editorial_planner,
)
from content_manager_bot.director.channel_memory import (
    ChannelMemory,
    get_channel_memory,
)
from content_manager_bot.director.self_reviewer import (
    SelfReviewer,
    get_self_reviewer,
)
from content_manager_bot.director.reflection_engine import (
    ReflectionEngine,
    get_reflection_engine,
)
from content_manager_bot.director.competitor_analyzer import (
    CompetitorAnalyzer,
    get_competitor_analyzer,
)
from content_manager_bot.director.trend_detector import (
    TrendDetector,
    get_trend_detector,
)

__all__ = [
    "PerformanceAnalyzer", "get_performance_analyzer",
    "EditorialPlanner", "get_editorial_planner",
    "ChannelMemory", "get_channel_memory",
    "SelfReviewer", "get_self_reviewer",
    "ReflectionEngine", "get_reflection_engine",
    "CompetitorAnalyzer", "get_competitor_analyzer",
    "TrendDetector", "get_trend_detector",
]
