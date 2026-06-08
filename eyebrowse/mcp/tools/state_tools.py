"""State tools: storage_state save + HAR export."""
from __future__ import annotations

import os

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_storage_state(session_id: str | None = None, path: str | None = None) -> str:
        """Save cookies + localStorage to a JSON file. Reload it later via
        browser_new_session(storage_state=path). Returns the file path."""
        eb = state.get_engine()
        s = await eb.ensure_session(session_id)
        if not path:
            os.makedirs(eb.settings.data_dir, exist_ok=True)
            path = os.path.join(eb.settings.data_dir, f"storage_{s.id}.json")
        return await s.save_storage_state(path)

    @mcp.tool()
    async def browser_har_export(
        session_id: str | None = None,
        output_path: str | None = None,
    ) -> str:
        """Finalize and return the HAR file path for a recording session.

        NOTE: This CLOSES the session — Playwright only flushes the HAR buffer when
        the browser context closes. The session must have been created with record_har=True.

        output_path: copy the finished HAR to this path (e.g. 'results/run1.har').
            If omitted, the HAR stays at its auto-generated path under data/har/.

        Non-destructive checkpoint pattern (to keep browsing after capturing traffic):
          1. browser_storage_state(path='data/checkpoint.json')   # save auth/cookies
          2. browser_har_export()                                  # closes session, flushes HAR
          3. browser_new_session(storage_state='data/checkpoint.json')  # resume
        """
        return await state.get_engine().export_har(session_id, output_path=output_path)
