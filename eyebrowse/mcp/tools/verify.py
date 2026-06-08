"""Assertion tools (granular) — check page state without parsing snapshots."""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_verify_element_visible(ref: str, session_id: str | None = None) -> dict:
        """Assert an element (by ref) is visible. Returns {ok, ...}."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.verify(visible_ref=ref)

    @mcp.tool()
    async def browser_verify_element_hidden(ref: str, session_id: str | None = None) -> dict:
        """Assert an element (by ref) is hidden/absent. Returns {ok, ...}."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.verify(hidden_ref=ref)

    @mcp.tool()
    async def browser_verify_text_visible(text: str, session_id: str | None = None) -> dict:
        """Assert some visible text appears on the page. Returns {ok, ...}."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.verify(text=text)

    @mcp.tool()
    async def browser_verify_value(ref: str, value: str, session_id: str | None = None) -> dict:
        """Assert an input/element (by ref) has the expected value. Returns {ok, ...}."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.verify(value_ref=ref, value=value)
