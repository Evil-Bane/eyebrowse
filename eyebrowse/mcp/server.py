"""FastMCP entrypoint — a stateful stdio server holding one EyeBrowse engine.

Run directly (``uv run eyebrowse-mcp`` / ``python -m eyebrowse.mcp.server``) or register
with Claude Code (``claude mcp add eyebrowse uv run eyebrowse-mcp``). Statefulness is
deliberate: live browser/context/page objects persist in memory across tool calls, so
``stateless_http`` is left at its default (False).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from ..api import EyeBrowse
from . import state
from .tools import register_all

INSTRUCTIONS = (
    "EyeBrowse drives a real, stealthy browser. Typical loop: browser_navigate(url) -> "
    "read the ARIA snapshot -> act on elements by their [ref=...] handle "
    "(browser_click/browser_type/...). Each action returns a fresh snapshot. A default "
    "session is created automatically; manage extra sessions with browser_new_session."
)


@asynccontextmanager
async def _lifespan(server: FastMCP):
    engine = EyeBrowse()
    state.set_engine(engine)
    try:
        yield {"engine": engine}
    finally:
        await engine.aclose()
        state.set_engine(None)


mcp = FastMCP("EyeBrowse", instructions=INSTRUCTIONS, lifespan=_lifespan)
register_all(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
