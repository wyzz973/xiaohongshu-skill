"""Daily rate limiter — enforces safety limits via persistent counter file.

Limits are loaded from strategy.json at runtime, falling back to safe defaults.
"""
from __future__ import annotations
import json, os, logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("xhs-cli")

_WORKSPACE = os.environ.get("XHS_WORKSPACE", os.path.expanduser("~/xhs-workspace"))
_COUNTER_DIR = os.path.join(_WORKSPACE, "logs")
_COUNTER_FILE = os.path.join(_COUNTER_DIR, "daily-quota.json")
_STRATEGY_FILE = os.path.join(_WORKSPACE, "strategy.json")

# Safe defaults — used only when strategy.json is missing or invalid
_SAFE_DEFAULTS = {
    "comment": 100,
    "like": 50,
    "publish": 4,
    "favorite": 50,
}


def _load_limits_from_strategy() -> dict:
    """Load limits from strategy.json, mapping config fields to action keys."""
    try:
        with open(_STRATEGY_FILE, "r", encoding="utf-8") as f:
            strategy = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("无法读取 strategy.json，使用安全默认限额")
        return _SAFE_DEFAULTS.copy()

    safety = strategy.get("safety", {})
    schedule = strategy.get("schedule", {})

    limits = {
        "comment": safety.get("daily_comment_limit", _SAFE_DEFAULTS["comment"]),
        "like": safety.get("daily_like_limit", _SAFE_DEFAULTS["like"]),
        "favorite": _SAFE_DEFAULTS["favorite"],
        "publish": schedule.get("publish_count_per_day",
                   strategy.get("content_strategy", {}).get("publish_count_per_day",
                   _SAFE_DEFAULTS["publish"])),
    }

    # Validate: limits must be positive integers
    for key, val in limits.items():
        if not isinstance(val, int) or val < 0:
            logger.warning("strategy.json 限额无效 %s=%s，使用默认值 %d", key, val, _SAFE_DEFAULTS[key])
            limits[key] = _SAFE_DEFAULTS[key]

    return limits


def get_limits() -> dict:
    """Get current effective limits (from strategy.json or safe defaults)."""
    return _load_limits_from_strategy()


def _load_counters() -> dict:
    """Load today's counters. Reset if date changed."""
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    try:
        with open(_COUNTER_FILE, "r") as f:
            data = json.load(f)
        if data.get("date") != today:
            return {"date": today, "counts": {}}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"date": today, "counts": {}}


def _save_counters(data: dict) -> None:
    os.makedirs(_COUNTER_DIR, exist_ok=True)
    tmp = _COUNTER_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _COUNTER_FILE)


def check_limit(action: str) -> tuple[bool, int, int]:
    """Check if action is within daily limit. Returns (allowed, current_count, limit)."""
    limits = _load_limits_from_strategy()
    limit = limits.get(action, 999)
    data = _load_counters()
    current = data.get("counts", {}).get(action, 0)
    return current < limit, current, limit


def increment(action: str) -> int:
    """Increment counter for action. Returns new count."""
    data = _load_counters()
    counts = data.setdefault("counts", {})
    counts[action] = counts.get(action, 0) + 1
    _save_counters(data)
    return counts[action]


def get_status() -> dict:
    """Get all current counters and limits."""
    data = _load_counters()
    return {
        "date": data.get("date"),
        "counts": data.get("counts", {}),
        "limits": _load_limits_from_strategy(),
    }
