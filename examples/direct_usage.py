"""Direct-library usage of EyeBrowse — no MCP involved.

Proves the engine works the way a library consumer uses it: import the façade,
open a session, and drive navigate -> snapshot -> type -> click -> evaluate -> screenshot
using ref handles from the ARIA snapshot.

Run:  uv run python examples/direct_usage.py
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from eyebrowse import EyeBrowse

DEMO_HTML = """<!doctype html><html><head><meta charset='utf-8'><title>EyeBrowse demo</title></head>
<body>
<h1>EyeBrowse demo</h1>
<label>Your name <input id='name' aria-label='Your name'></label>
<button id='greet'>Greet</button>
<p id='out'></p>
<script>
document.getElementById('greet').addEventListener('click', function () {
  document.getElementById('out').textContent = 'Hello ' + document.getElementById('name').value + '!';
});
</script>
</body></html>
"""


def _ref_for(snapshot: str, pattern: str) -> str:
    m = re.search(pattern + r'.*?\[ref=(e\d+)\]', snapshot)
    if not m:
        raise AssertionError(f"no ref matching {pattern!r} in snapshot:\n{snapshot}")
    return m.group(1)


async def main() -> None:
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    demo = data_dir / "demo.html"
    demo.write_text(DEMO_HTML, encoding="utf-8")

    eb = EyeBrowse()
    try:
        # Fast, deterministic run: override the production stealth defaults.
        async with eb.session(headless=True, geoip=False, humanize=False) as s:
            snap = await s.navigate(demo.resolve().as_uri())
            print("=== initial snapshot ===")
            print(snap)

            name_ref = _ref_for(snap, r'textbox')
            greet_ref = _ref_for(snap, r'button "Greet"')
            print(f"\nresolved refs -> name={name_ref} greet={greet_ref}")

            await s.type(name_ref, "Ada")
            await s.click(greet_ref)

            out = await s.evaluate("document.getElementById('out').textContent")
            print(f"\nevaluate -> out textContent = {out!r}")
            assert out == "Hello Ada!", f"click/type did not take effect: {out!r}"

            shot = data_dir / "demo.png"
            png = await s.screenshot(full_page=True)
            shot.write_bytes(png)
            print(f"screenshot -> {shot} ({len(png)} bytes)")

            print("\nsessions:", eb.list_sessions())
        print("\nDIRECT_OK")
    finally:
        await eb.aclose()


if __name__ == "__main__":
    asyncio.run(main())
