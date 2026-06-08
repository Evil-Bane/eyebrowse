"""Process-wide handle to the live EyeBrowse engine.

The MCP server is a single stateful stdio process, so one in-memory engine instance
is shared by every tool call. The lifespan sets it on startup and clears it on
shutdown; tools fetch it via :func:`get_engine`.
"""
from __future__ import annotations

from ..api import EyeBrowse

_engine: EyeBrowse | None = None


def set_engine(engine: EyeBrowse | None) -> None:
    global _engine
    _engine = engine


def get_engine() -> EyeBrowse:
    if _engine is None:
        raise RuntimeError("EyeBrowse engine is not initialised (server lifespan not started).")
    return _engine
