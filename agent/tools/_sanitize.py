"""Recursive NaN/Inf scrubber applied to every tool's return value.

LiteLLM's httpx client serializes outgoing request bodies with
allow_nan=False, so any NaN/Inf hiding inside a tool result raises
"Out of range float values are not JSON compliant".
"""
from __future__ import annotations

import math
from functools import wraps
from typing import Any, Callable


def clean_nan(obj: Any) -> Any:
    """Recursively replace NaN/Inf floats with None; leave other values alone."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        cleaned = [clean_nan(v) for v in obj]
        return cleaned if isinstance(obj, list) else tuple(cleaned)
    return obj


def nan_safe(fn: Callable) -> Callable:
    """Decorator: scrub NaN/Inf out of any tool's return value."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        return clean_nan(fn(*args, **kwargs))

    return wrapper
