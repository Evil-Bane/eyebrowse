"""Coordinate (vision-style) mouse tools — for canvas/maps/drag where refs don't apply."""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_mouse_move(x: float, y: float, session_id: str | None = None) -> str:
        """Move the mouse to absolute page coordinates (x, y)."""
        s = await state.get_engine().ensure_session(session_id)
        await s.mouse_move(x, y)
        return f"moved to {x},{y}"

    @mcp.tool()
    async def browser_mouse_click(
        x: float, y: float, button: str = "left", clicks: int = 1, session_id: str | None = None
    ) -> str:
        """Click at absolute coordinates (x, y). button: left|right|middle; clicks for multi-click."""
        s = await state.get_engine().ensure_session(session_id)
        await s.mouse_click(x, y, button=button, clicks=clicks)
        return f"clicked {x},{y}"

    @mcp.tool()
    async def browser_mouse_down(button: str = "left", session_id: str | None = None) -> str:
        """Press a mouse button down (at the current position)."""
        s = await state.get_engine().ensure_session(session_id)
        await s.mouse_down(button=button)
        return "mouse down"

    @mcp.tool()
    async def browser_mouse_up(button: str = "left", session_id: str | None = None) -> str:
        """Release a mouse button (at the current position)."""
        s = await state.get_engine().ensure_session(session_id)
        await s.mouse_up(button=button)
        return "mouse up"

    @mcp.tool()
    async def browser_mouse_wheel(delta_x: float = 0, delta_y: float = 0, session_id: str | None = None) -> str:
        """Scroll the mouse wheel by (delta_x, delta_y) pixels."""
        s = await state.get_engine().ensure_session(session_id)
        await s.mouse_wheel(delta_x, delta_y)
        return f"wheel {delta_x},{delta_y}"

    @mcp.tool()
    async def browser_mouse_drag(
        x1: float, y1: float, x2: float, y2: float, session_id: str | None = None
    ) -> str:
        """Drag from (x1, y1) to (x2, y2) with the left button held."""
        s = await state.get_engine().ensure_session(session_id)
        await s.mouse_drag(x1, y1, x2, y2)
        return f"dragged {x1},{y1} -> {x2},{y2}"
