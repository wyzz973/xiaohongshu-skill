"""Daily rate limiter — enforces safety limits via persistent counter file."""
from __future__ import annotations
import json, os, time, logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("xhs-cli")

_COUNTER_DIR = os.path.join(os.environ.get("XHS_WORKSPACE", os.path.expanduser("~/xhs-workspace")), "logs")
_COUNTER_FILE = os.path.join(_COUNTER_DIR, "daily-quota.json")

# Default limits (can be overridden by strategy.json)
DEFAULT_LIMITS = {
    "comment": 100,    # post-comment + reply-comment per day
    "like": 50,        # like-feed + like-notification per day
    "publish": 4,      # all publish types per day
    "favorite": 50,    # favorite-feed per day
}

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

def check_limit(action: str, limits: dict | None = None) -> tuple[bool, int, int]:
    """Check if action is within daily limit. Returns (allowed, current_count, limit)."""
    limits = limits or DEFAULT_LIMITS
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

def check_and_increment(action: str, limits: dict | None = None) -> tuple[bool, int, int]:
    """Check limit and increment if allowed. Returns (allowed, new_count, limit).
    If not allowed, does NOT increment."""
    allowed, current, limit = check_limit(action, limits)
    if allowed:
        new_count = increment(action)
        return True, new_count, limit
    return False, current, limit

def get_status() -> dict:
    """Get all current counters and limits."""
    data = _load_counters()
    return {
        "date": data.get("date"),
        "counts": data.get("counts", {}),
        "limits": DEFAULT_LIMITS,
    }
