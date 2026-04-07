"""Validate strategy.json on CLI startup."""
from __future__ import annotations
import json, os, sys, logging

logger = logging.getLogger("xhs-cli")

REQUIRED_FIELDS = [
    "account.nickname",
    "account.xhs_id",
    "persona.type",
    "content_strategy.pillars",
    "safety.daily_comment_limit",
    "safety.daily_like_limit",
]

def validate_strategy(path: str) -> dict | None:
    """Load and validate strategy.json. Returns parsed dict or None on error."""
    if not os.path.exists(path):
        logger.warning("strategy.json not found: %s (using defaults)", path)
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            strategy = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("strategy.json JSON parse error: %s", e)
        return None

    # Check required fields
    missing = []
    for field_path in REQUIRED_FIELDS:
        parts = field_path.split(".")
        obj = strategy
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                missing.append(field_path)
                break

    if missing:
        logger.warning("strategy.json missing fields: %s", missing)

    # Validate pillar weights sum
    pillars = strategy.get("content_strategy", {}).get("pillars", [])
    if pillars:
        weight_sum = sum(p.get("weight", 0) for p in pillars)
        if abs(weight_sum - 1.0) > 0.01:
            logger.warning("Pillar weights sum to %.2f (expected 1.0)", weight_sum)

    # Validate safety limits are positive
    safety = strategy.get("safety", {})
    for key in ["daily_comment_limit", "daily_like_limit"]:
        val = safety.get(key)
        if val is not None and (not isinstance(val, int) or val < 0):
            logger.error("Invalid safety.%s: %s", key, val)

    return strategy
