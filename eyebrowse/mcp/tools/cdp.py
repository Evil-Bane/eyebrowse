"""CDP-backed tools (Chrome DevTools Protocol).

Trusted cursorless clicks, a raw CDP escape hatch, single-file MHTML capture, and PDF export —
all unlocked by the Chromium engine via Playwright's new_cdp_session().
"""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_cdp_click(
        ref: str, session_id: str | None = None, button: str = "left", double: bool = False
    ) -> str:
        """Click an element by its [ref=...] using a TRUSTED, cursorless CDP input event.

        Preferred over browser_mouse_click: no visible cursor, no pixel guessing (the click point
        is computed from the element's own box), and the event is isTrusted=true — so it passes
        bot-detection that flags DOM .click()/dispatchEvent (isTrusted=false). Chromium only.
        Returns a fresh ARIA snapshot.
        """
        s = await state.get_engine().ensure_session(session_id)
        await s.cdp_click(ref, button=button, clicks=2 if double else 1)
        return await s.snapshot()

    @mcp.tool()
    async def browser_cdp_send(
        method: str, params: dict | None = None, session_id: str | None = None
    ) -> dict:
        """Send a raw Chrome DevTools Protocol command and return its result.

        Escape hatch for any CDP capability not wrapped elsewhere — e.g.
        method='Network.getResponseBody' {requestId}, 'Network.getRequestPostData' {requestId},
        'Emulation.setGeolocationOverride', 'Emulation.setDeviceMetricsOverride',
        'Network.emulateNetworkConditions', 'Performance.getMetrics'. Chromium only.
        """
        s = await state.get_engine().ensure_session(session_id)
        return await s.cdp_send(method, params)

    @mcp.tool()
    async def browser_capture_mhtml(output_path: str, session_id: str | None = None) -> str:
        """Save the full page as a single-file MHTML archive (iframes + shadow DOM + external
        resources + inline styles) via CDP Page.captureSnapshot — captures the exact page state
        for debugging/forensics. Chromium only. Returns the saved file path.
        """
        s = await state.get_engine().ensure_session(session_id)
        return await s.capture_mhtml(output_path)

    @mcp.tool()
    async def browser_pdf_save(output_path: str, session_id: str | None = None) -> str:
        """Save the current page as a PDF file. Chromium only. Returns the saved file path."""
        s = await state.get_engine().ensure_session(session_id)
        return await s.save_pdf(output_path)
