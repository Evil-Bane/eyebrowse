"""Proxy configuration + a pluggable rotation-provider interface.

The engine is provider-agnostic: it accepts a ``ProxyConfig`` (Playwright's dict
format) or any ``ProxyProvider`` that yields one. Residential rotation lives behind
this interface so workflows decide *whether* to rotate — the engine just consumes it.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProxyConfig:
    """A single proxy, mapped to Playwright's expected dict shape."""

    server: str
    username: str | None = None
    password: str | None = None

    def to_playwright(self) -> dict[str, str]:
        d: dict[str, str] = {"server": self.server}
        if self.username:
            d["username"] = self.username
        if self.password:
            d["password"] = self.password
        return d

    @classmethod
    def parse(cls, url: str) -> "ProxyConfig":
        """Parse a proxy URL string, e.g. ``http://user:pass@host:8080`` or ``host:8080``."""
        from urllib.parse import urlparse

        parsed = urlparse(url if "://" in url else f"http://{url}")
        host = parsed.hostname or ""
        server = f"{parsed.scheme}://{host}"
        if parsed.port:
            server += f":{parsed.port}"
        return cls(server=server, username=parsed.username or None, password=parsed.password or None)

    @classmethod
    def coerce(cls, proxy) -> "ProxyConfig | None":
        """Accept None / a URL string / a dict / a ProxyConfig and normalize to one."""
        if proxy is None:
            return None
        if isinstance(proxy, ProxyConfig):
            return proxy
        if isinstance(proxy, str):
            return cls.parse(proxy)
        if isinstance(proxy, dict):
            return cls(proxy["server"], proxy.get("username"), proxy.get("password"))
        raise TypeError(f"Unsupported proxy value {proxy!r} (use a URL string, dict, or ProxyConfig)")

    @classmethod
    def from_settings(cls, settings) -> "ProxyConfig | None":
        if getattr(settings, "proxy_server", None):
            return cls(settings.proxy_server, settings.proxy_username, settings.proxy_password)
        return None


class ProxyProvider(ABC):
    """Pluggable source of proxies. Implement for a residential rotating pool."""

    @abstractmethod
    async def acquire(self) -> ProxyConfig: ...

    async def release(self, proxy: ProxyConfig) -> None:  # noqa: D401 - optional hook
        return None


class StaticProxyProvider(ProxyProvider):
    """Always hands back the same proxy (the simplest provider)."""

    def __init__(self, proxy: ProxyConfig):
        self._proxy = proxy

    async def acquire(self) -> ProxyConfig:
        return self._proxy
