"""Extraction tool (M5, Crawl4AI raw: feed — markdown only, no LLM)."""
from __future__ import annotations

import importlib.util
import logging
from typing import Any

from .. import state

_log = logging.getLogger("eyebrowse.mcp.extract")


def register(mcp) -> None:
    # Don't advertise browser_extract unless its optional dependency is actually installed — calling
    # it without crawl4ai (the `extract` extra) just raises RuntimeError and wastes the agent a step.
    # Install with: uv sync --extra extract.
    if importlib.util.find_spec("crawl4ai") is None:
        _log.info("browser_extract not registered: the 'extract' extra (crawl4ai) is not installed")
        return

    @mcp.tool()
    async def browser_extract(output_path: str | None = None, session_id: str | None = None) -> Any:
        """Extract the current page as clean, token-efficient markdown (no LLM involved).

        Returns the markdown string. If output_path is given, the markdown is written to
        that file and {path, chars} is returned instead — so you can pick a path and fetch
        the content from there. You (the agent) do any further structuring/extraction.
        """
        return await state.get_engine().extract(session_id=session_id, output_path=output_path)
