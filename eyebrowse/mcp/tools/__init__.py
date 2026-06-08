"""Tool registration, grouped by concern (1:1 over the façade)."""
from __future__ import annotations

from . import (
    captcha,
    cdp,
    cookies,
    devtools,
    emulate,
    extract,
    identity,
    interact,
    mouse,
    navigate,
    netcontrol,
    network,
    observe,
    sessions,
    state_tools,
    verify,
    webstorage,
)


def register_all(mcp) -> None:
    sessions.register(mcp)
    navigate.register(mcp)
    observe.register(mcp)
    interact.register(mcp)
    network.register(mcp)
    state_tools.register(mcp)
    identity.register(mcp)
    captcha.register(mcp)
    extract.register(mcp)
    cookies.register(mcp)
    webstorage.register(mcp)
    mouse.register(mcp)
    netcontrol.register(mcp)
    verify.register(mcp)
    devtools.register(mcp)
    emulate.register(mcp)
    cdp.register(mcp)
