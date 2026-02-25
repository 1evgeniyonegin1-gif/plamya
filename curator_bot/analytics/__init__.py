"""
Модуль аналитики воронки продаж
"""

from curator_bot.analytics.funnel_stats import (
    get_funnel_stats,
    calculate_lead_score,
)
from curator_bot.analytics.lead_scoring import (
    update_lead_score,
    get_hot_leads,
)

__all__ = [
    "get_funnel_stats",
    "calculate_lead_score",
    "update_lead_score",
    "get_hot_leads",
]
