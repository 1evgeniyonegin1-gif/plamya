"""Example agent configuration."""

from pathlib import Path

# PLAMYA state
PLAMYA_HOME = Path.home() / ".plamya"
AGENT_DIR = PLAMYA_HOME / "chappie"
SHARED_DIR = PLAMYA_HOME / "shared"
CONFIG_FILE = PLAMYA_HOME / "embers" / "chappie.json"

# Safety limits (hard caps, cannot be overridden)
LIMITS = {
    "max_posts_per_day": 3,
    "max_dms_per_day": 3,
    "max_api_calls_per_day": 50,
    "min_interval_post_sec": 10800,   # 3 hours
}

# Work hours (UTC offset)
WORK_HOURS_START = 9
WORK_HOURS_END = 22
UTC_OFFSET = 3  # MSK
