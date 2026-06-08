"""Navigation tools."""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_navigate(
        url: str,
        session_id: str | None = None,
        wait_until: str = "domcontentloaded",
        timeout_ms: float | None = None,
    ) -> str:
        """Navigate to a URL. Returns the page's ARIA snapshot (with [ref=...] handles).

        wait_until: when to consider navigation done —
            'domcontentloaded' (default, fast: DOM parsed) | 'commit' (fastest: response
            started) | 'load' (waits for ALL resources — slow/unreliable on heavy or proxied
            sites) | 'networkidle'. Prefer the default and then browser_wait_for a specific
            element; only use 'load' for simple static pages.
        timeout_ms: max navigation wait; None = the engine's configured navigation timeout.
        Auto-creates a session if none exists.
        """
        s = await state.get_engine().ensure_session(session_id)
        return await s.navigate(url, wait_until=wait_until, timeout_ms=timeout_ms)

    @mcp.tool()
    async def browser_navigate_back(session_id: str | None = None) -> str:
        """Go back one entry in history. Returns the new page's ARIA snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.navigate_back()

    @mcp.tool()
    async def browser_navigate_forward(session_id: str | None = None) -> str:
        """Go forward one entry in history. Returns the new page's ARIA snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.navigate_forward()

    @mcp.tool()
    async def browser_reload(session_id: str | None = None) -> str:
        """Reload the current page. Returns the page's ARIA snapshot."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.reload()

    @mcp.tool()
    async def browser_switch_to_popup(
        session_id: str | None = None,
        timeout_ms: float = 5000,
    ) -> str:
        """Switch the active page to the most recently opened popup or new tab.

        Use this after triggering an OAuth / SSO flow (Google Sign-In, GitHub OAuth,
        etc.) or any action that calls window.open() or opens a target=_blank link.
        The tool waits up to timeout_ms for the new window to open, then makes it the
        active page and returns its ARIA snapshot. To go back to the original tab
        afterward, use browser_tabs(action='select', index=0)."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.switch_to_popup(timeout_ms=timeout_ms)

    @mcp.tool()
    async def browser_tabs(
        action: str = "list",
        index: int | None = None,
        url: str | None = None,
        session_id: str | None = None,
    ) -> list[dict]:
        """Manage tabs. action: list | new | select | close (index for select/close,
        url optional for new). Returns the resulting tab list."""
        s = await state.get_engine().ensure_session(session_id)
        if action == "new":
            await s.new_tab(url)
        elif action == "select":
            if index is None:
                raise ValueError("select requires index")
            await s.select_tab(index)
        elif action == "close":
            if index is None:
                raise ValueError("close requires index")
            await s.close_tab(index)
        elif action != "list":
            raise ValueError(f"unknown tabs action {action!r}")
        return await s.list_tabs()
