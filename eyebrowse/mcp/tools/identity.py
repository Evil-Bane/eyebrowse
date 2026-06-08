"""Identity & proxy rotation tools (M3)."""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_new_identity(
        persistent: bool = False,
        label: str | None = None,
        proxy_url: str | None = None,
        proxy_server: str | None = None,
        proxy_username: str | None = None,
        proxy_password: str | None = None,
        no_proxy: bool = False,
    ) -> dict:
        """Start a fresh browser identity in a new session: a novel fingerprint
        (randomized OS + screen) with isolated storage, optionally paired with a proxy.
        Proxyless by default; pass proxy_url ('http://user:pass@host:port') or
        proxy_server[+username/password] to pair an IP. persistent=True mints a reusable
        profile dir. Returns the new session info."""
        from ...proxy import ProxyConfig

        eb = state.get_engine()
        if proxy_url:
            proxy = ProxyConfig.parse(proxy_url)
        elif proxy_server:
            proxy = ProxyConfig(proxy_server, proxy_username, proxy_password)
        else:
            proxy = None
        s = await eb.rotate_identity(persistent=persistent, proxy=proxy, no_proxy=no_proxy, label=label)
        return {
            "session_id": s.id,
            "identity_os": getattr(s.identity, "os", None),
            "persistent": s.persistent,
            "proxied": s.proxy is not None,
        }

    @mcp.tool()
    async def browser_set_proxy(
        server: str,
        username: str | None = None,
        password: str | None = None,
    ) -> str:
        """Pin a proxy as the default for subsequent sessions/identities.
        (Proxies are bound at launch, so existing sessions are unaffected.)"""
        eb = state.get_engine()
        eb.set_static_proxy(server, username, password)
        return f"default proxy set -> {server}"
