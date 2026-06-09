"""Observation tools: snapshot, screenshot, console, downloads."""
from __future__ import annotations

import os

from mcp.server.fastmcp import Image

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_snapshot(session_id: str | None = None, depth: int | None = None) -> str:
        """Capture the page's ARIA accessibility tree with [ref=...] handles.

        This is the primary way to 'see' a page: it lists actionable elements (roles +
        names + refs) without CSS/markup noise. Pass a ref from here to click/type/hover.
        Frame-hosted elements get prefixed refs like 'f1e36' (iframe 1, element 36).
        Shadow DOM elements appear with plain eN refs — the locator engine pierces them.
        """
        s = await state.get_engine().ensure_session(session_id)
        return await s.snapshot(depth=depth)

    @mcp.tool()
    async def browser_snapshot_frame(
        frame_ref: str,
        session_id: str | None = None,
        depth: int | None = None,
    ) -> str:
        """Snapshot a specific child frame directly. Use when browser_snapshot returns
        an iframe node with empty/collapsed children — snapshotting the frame is reliable
        (works for same-origin AND cross-origin frames).

        frame_ref: a frame id ('f1'), an element ref inside the frame ('f1e36'), or the
        <iframe> element's own ref ('e81'). Returns the frame's ARIA tree with refs
        rewritten to 'fNeM' form so they're directly usable with click/type/etc."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.snapshot_frame(frame_ref, depth=depth)

    @mcp.tool()
    async def browser_screenshot(
        session_id: str | None = None,
        full_page: bool = False,
        ref: str | None = None,
        output_path: str | None = None,
    ) -> Image | str:
        """Take a PNG screenshot. By default captures the visible viewport; full_page=True
        captures the entire scrollable page; ref captures a single element.

        output_path: if given, the PNG is WRITTEN TO THAT FILE and the absolute path is returned
        as text (instead of returning the image bytes). Use this to hand a screenshot to an
        out-of-band vision/OCR tool without routing the (large) image bytes through the caller —
        e.g. a text-only LLM driver that delegates 'seeing' to a separate vision model."""
        s = await state.get_engine().ensure_session(session_id)
        data = await s.screenshot(full_page=full_page, ref=ref)
        if output_path:
            path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(data)
            return f"Screenshot saved to: {path} ({len(data)} bytes). Pass this exact path to a vision/analysis tool."
        return Image(data=data, format="png")

    @mcp.tool()
    async def browser_resize(width: int, height: int, session_id: str | None = None) -> str:
        """Resize the page viewport (e.g. 1920x1080). Affects layout and screenshot size."""
        s = await state.get_engine().ensure_session(session_id)
        await s.resize(width, height)
        return f"viewport set to {width}x{height}"

    @mcp.tool()
    async def browser_console_messages(session_id: str | None = None) -> list[dict]:
        """Return console messages collected on the current page (type + text)."""
        s = await state.get_engine().ensure_session(session_id)
        return s.get_console_messages()

    @mcp.tool()
    async def browser_wait_for_download(
        session_id: str | None = None,
        save_dir: str = "data/downloads",
        timeout_ms: float = 30000,
    ) -> str:
        """Wait for a file download to complete and return its saved path.

        Call this before (or immediately after) clicking a download button.
        The first download event is captured, saved to save_dir, and the
        absolute file path is returned. timeout_ms: max wait (default 30s)."""
        s = await state.get_engine().ensure_session(session_id)
        path = await s.wait_for_download(save_dir=save_dir, timeout_ms=timeout_ms)
        return path
