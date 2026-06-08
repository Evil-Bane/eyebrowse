"""The browser engine internals: launch (CloakBrowser/Chromium) + session lifecycle."""
from __future__ import annotations

from .engine import BrowserEngine, LaunchResult
from .session import Session, SessionRegistry

__all__ = ["BrowserEngine", "LaunchResult", "Session", "SessionRegistry"]
