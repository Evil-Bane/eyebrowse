"""Emulation tools: geolocation, extra HTTP headers, browser permissions.

(Note: media emulation / prefers-color-scheme isn't a dedicated tool but is reachable via
browser_cdp_send → Emulation.setEmulatedMedia.)
"""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_set_geolocation(
        latitude: float, longitude: float, session_id: str | None = None
    ) -> str:
        """Override the geolocation the page reads (note: geoip already aligns geo to the IP)."""
        s = await state.get_engine().ensure_session(session_id)
        await s.set_geolocation(latitude, longitude)
        return f"geolocation set to {latitude},{longitude}"

    @mcp.tool()
    async def browser_set_extra_headers(headers: dict, session_id: str | None = None) -> str:
        """Set extra HTTP headers sent with every request in this session."""
        s = await state.get_engine().ensure_session(session_id)
        await s.set_extra_headers(headers)
        return f"set {len(headers)} header(s)"

    @mcp.tool()
    async def browser_grant_permissions(
        permissions: list[str],
        origin: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Pre-grant browser permissions so the native prompt never blocks the flow.

        permissions: list of permission names, e.g. ['geolocation'], ['notifications'],
            ['camera'], ['microphone'], ['clipboard-read'], ['clipboard-write'].
        origin: restrict the grant to a specific origin (e.g. 'https://example.com');
            omit to apply session-wide.

        Call this before navigating to a page that requests permissions, or immediately
        when a permission prompt appears (it will dismiss the prompt automatically)."""
        s = await state.get_engine().ensure_session(session_id)
        await s.grant_permissions(permissions, origin=origin)
        scope = f" for {origin}" if origin else ""
        return f"granted {permissions}{scope}"
