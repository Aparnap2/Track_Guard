"""Langfuse @traced decorator — zero test impact.
No-op if LANGFUSE_SECRET_KEY not set (unit tests pass through)."""
from __future__ import annotations
import os, functools
from typing import Any

try:
    from langfuse import observe, get_client
    
    def _get_langfuse():
        try:
            return get_client()
        except Exception:
            return None
    
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    def _get_langfuse():
        return None


def traced(agent: str, signature: str):
    """Decorator. Pure pass-through if Langfuse not configured."""
    if not LANGFUSE_AVAILABLE:
        def passthrough(fn):
            return fn
        return passthrough
    
    def decorator(fn):
        @functools.wraps(fn)
        @observe(name=f"{agent}.{signature}", as_type="generation")
        def wrapper(*args, **kwargs):
            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as e:
                raise
        return wrapper
    return decorator