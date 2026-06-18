"""EyeBrowse — a stealthy, LLM-drivable browser-control engine.

Library-first: the public façade exported here *is* the product. The MCP adapter
(``eyebrowse.mcp``) is a thin 1:1 wrapper over this same API.

    from eyebrowse import EyeBrowse

    eb = EyeBrowse()
    async with eb.session() as s:
        await s.navigate("https://example.com")
        print(await s.snapshot())
"""
from __future__ import annotations

from .api import EyeBrowse
from .config import Settings, get_settings
from .engine import Session
from .identity import Identity, random_identity
from .proxy import ProxyConfig, ProxyProvider, StaticProxyProvider

__version__ = "0.3.10"

__all__ = [
    "__version__",
    "EyeBrowse",
    "Session",
    "Settings",
    "get_settings",
    "Identity",
    "random_identity",
    "ProxyConfig",
    "ProxyProvider",
    "StaticProxyProvider",
]
