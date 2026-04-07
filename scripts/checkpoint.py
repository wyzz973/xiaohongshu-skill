"""Publish checkpoint — tracks multi-step publish progress for crash recovery."""
from __future__ import annotations
import json, os, time, logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("xhs-cli")

_CHECKPOINT_DIR = os.path.join(
    os.environ.get("XHS_WORKSPACE", os.path.expanduser("~/xhs-workspace")),
    "logs"
)
_CHECKPOINT_FILE = os.path.join(_CHECKPOINT_DIR, "publish-checkpoint.json")


def save_checkpoint(phase: str, data: dict) -> None:
    """Save checkpoint after a publish step completes."""
    checkpoint = {
        "phase": phase,  # "fill_done" | "template_done" | "publish_done"
        "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "data": data,
    }
    os.makedirs(_CHECKPOINT_DIR, exist_ok=True)
    tmp = _CHECKPOINT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _CHECKPOINT_FILE)
    logger.info("Checkpoint saved: phase=%s", phase)


def load_checkpoint() -> dict | None:
    """Load existing checkpoint. Returns None if no checkpoint exists."""
    try:
        with open(_CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Check if checkpoint is stale (> 2 hours old)
        ts = data.get("timestamp", "")
        if ts:
            from datetime import datetime as dt
            checkpoint_time = dt.fromisoformat(ts)
            now = datetime.now(timezone(timedelta(hours=8)))
            age_hours = (now - checkpoint_time).total_seconds() / 3600
            if age_hours > 2:
                logger.warning("Checkpoint is stale (%.1f hours old), ignoring", age_hours)
                clear_checkpoint()
                return None
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def clear_checkpoint() -> None:
    """Clear checkpoint after successful publish or explicit cancel."""
    try:
        os.remove(_CHECKPOINT_FILE)
        logger.info("Checkpoint cleared")
    except FileNotFoundError:
        pass
