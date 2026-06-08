"""localStorage / sessionStorage tools (granular, per-action)."""
from __future__ import annotations

from typing import Any

from .. import state


async def _sess(session_id):
    return await state.get_engine().ensure_session(session_id)


def register(mcp) -> None:
    # ── localStorage ──
    @mcp.tool()
    async def browser_localstorage_list(session_id: str | None = None) -> dict:
        """List all localStorage key/value pairs for the current origin."""
        return await (await _sess(session_id)).storage_list("local")

    @mcp.tool()
    async def browser_localstorage_get(key: str, session_id: str | None = None) -> Any:
        """Get a localStorage value by key (null if absent)."""
        return await (await _sess(session_id)).storage_get("local", key)

    @mcp.tool()
    async def browser_localstorage_set(key: str, value: str, session_id: str | None = None) -> str:
        """Set a localStorage key to a value."""
        await (await _sess(session_id)).storage_set("local", key, value)
        return "ok"

    @mcp.tool()
    async def browser_localstorage_remove(key: str, session_id: str | None = None) -> str:
        """Remove a localStorage key."""
        await (await _sess(session_id)).storage_remove("local", key)
        return "ok"

    @mcp.tool()
    async def browser_localstorage_clear(session_id: str | None = None) -> str:
        """Clear all localStorage for the current origin."""
        await (await _sess(session_id)).storage_clear("local")
        return "ok"

    # ── sessionStorage ──
    @mcp.tool()
    async def browser_sessionstorage_list(session_id: str | None = None) -> dict:
        """List all sessionStorage key/value pairs for the current origin."""
        return await (await _sess(session_id)).storage_list("session")

    @mcp.tool()
    async def browser_sessionstorage_get(key: str, session_id: str | None = None) -> Any:
        """Get a sessionStorage value by key (null if absent)."""
        return await (await _sess(session_id)).storage_get("session", key)

    @mcp.tool()
    async def browser_sessionstorage_set(key: str, value: str, session_id: str | None = None) -> str:
        """Set a sessionStorage key to a value."""
        await (await _sess(session_id)).storage_set("session", key, value)
        return "ok"

    @mcp.tool()
    async def browser_sessionstorage_remove(key: str, session_id: str | None = None) -> str:
        """Remove a sessionStorage key."""
        await (await _sess(session_id)).storage_remove("session", key)
        return "ok"

    @mcp.tool()
    async def browser_sessionstorage_clear(session_id: str | None = None) -> str:
        """Clear all sessionStorage for the current origin."""
        await (await _sess(session_id)).storage_clear("session")
        return "ok"
