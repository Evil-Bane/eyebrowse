"""Network control tools: block URLs, go offline."""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_block_urls(patterns: list[str], session_id: str | None = None) -> str:
        """Abort requests matching glob patterns (e.g. '**/*.png', '**/ads/**').
        Useful to save proxy bandwidth or strip trackers/images."""
        s = await state.get_engine().ensure_session(session_id)
        await s.block_urls(patterns)
        return f"blocking {len(patterns)} pattern(s)"

    @mcp.tool()
    async def browser_unblock_urls(session_id: str | None = None) -> str:
        """Remove all URL routes added via browser_block_urls or browser_mock_url."""
        s = await state.get_engine().ensure_session(session_id)
        await s.unblock_urls()
        return "unblocked"

    @mcp.tool()
    async def browser_set_offline(offline: bool = True, session_id: str | None = None) -> str:
        """Toggle the context's network offline/online (to test offline behavior)."""
        s = await state.get_engine().ensure_session(session_id)
        await s.set_offline(offline)
        return f"offline={offline}"

    @mcp.tool()
    async def browser_mock_url(
        pattern: str,
        status: int = 200,
        body: str = "",
        content_type: str = "text/plain",
        session_id: str | None = None,
    ) -> str:
        """Fulfill requests matching a glob pattern with a canned response (response mocking /
        fault injection). Cleared by browser_unblock_urls."""
        s = await state.get_engine().ensure_session(session_id)
        await s.mock_url(pattern, status=status, body=body, content_type=content_type)
        return f"mocking {pattern} -> {status}"
