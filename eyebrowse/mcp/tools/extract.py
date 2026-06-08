"""Extraction tool (M5, Crawl4AI raw: feed — markdown only, no LLM)."""
from __future__ import annotations

from typing import Any

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_extract(output_path: str | None = None, session_id: str | None = None) -> Any:
        """Extract the current page as clean, token-efficient markdown (no LLM involved).

        Returns the markdown string. If output_path is given, the markdown is written to
        that file and {path, chars} is returned instead — so you can pick a path and fetch
        the content from there. You (the agent) do any further structuring/extraction.
        """
        return await state.get_engine().extract(session_id=session_id, output_path=output_path)
