"""Debugging/devtools: highlight elements, generate a locator, Playwright tracing."""
from __future__ import annotations

import os

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_highlight(ref: str, session_id: str | None = None) -> str:
        """Draw a magenta outline around an element (by ref) — handy before a screenshot."""
        s = await state.get_engine().ensure_session(session_id)
        await s.highlight(ref)
        return f"highlighted {ref}"

    @mcp.tool()
    async def browser_clear_highlights(session_id: str | None = None) -> str:
        """Remove all highlight outlines added via browser_highlight."""
        s = await state.get_engine().ensure_session(session_id)
        await s.clear_highlights()
        return "cleared"

    @mcp.tool()
    async def browser_generate_locator(ref: str, session_id: str | None = None) -> str:
        """Return a stable CSS selector for an element (by ref) for use in code/tests."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.generate_locator(ref)

    @mcp.tool()
    async def browser_start_tracing(session_id: str | None = None) -> str:
        """Start a Playwright trace (screenshots + DOM snapshots) for later inspection."""
        s = await state.get_engine().ensure_session(session_id)
        await s.start_tracing()
        return "tracing started"

    @mcp.tool()
    async def browser_stop_tracing(path: str | None = None, session_id: str | None = None) -> str:
        """Stop tracing and write a trace.zip (open with `playwright show-trace`). Returns the path."""
        eb = state.get_engine()
        s = await eb.ensure_session(session_id)
        if not path:
            os.makedirs(eb.settings.data_dir, exist_ok=True)
            path = os.path.join(eb.settings.data_dir, f"trace_{s.id}.zip")
        return await s.stop_tracing(path)
