"""Produce the demo video for EyeBrowse → docs/demo.webm (native Playwright/Chromium video).

Records a short, well-paced browse with native video (`record_video`), overlaying a lightweight
browser-frame + caption banner (injected into the page itself, rendered by the real browser — no
Pillow/ffmpeg compositing) that narrates each action. `record_video` captures the page viewport,
so the overlay is what gives the clip its "ad" framing. Saves the native ``.webm``; convert it to
a GIF/MP4 for the README with ffmpeg:

    ffmpeg -i docs/demo.webm docs/demo.gif                       # autoplaying GIF
    ffmpeg -i docs/demo.webm -c:v libx264 -pix_fmt yuv420p docs/demo.mp4

Run:  uv run python examples/make_demo.py
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from eyebrowse import EyeBrowse

OUT = Path("docs/demo.webm")

# A top browser-frame bar (brand + traffic lights + URL) and a bottom caption banner, injected
# into the page DOM so they're part of the native recording. Re-injected after each navigation.
_OVERLAY_JS = r"""(args) => {
  const {url, caption} = args;
  const mk = (id, css) => {
    let e = document.getElementById(id);
    if (!e) { e = document.createElement('div'); e.id = id; (document.body || document.documentElement).appendChild(e); }
    Object.assign(e.style, css);
    return e;
  };
  const bar = mk('__eb_bar', {
    position: 'fixed', top: '0', left: '0', right: '0', height: '44px', zIndex: '2147483647',
    background: '#161b22', borderBottom: '1px solid #30363d', display: 'flex', alignItems: 'center',
    padding: '0 16px', boxSizing: 'border-box', font: '600 14px "Segoe UI", system-ui, sans-serif',
    color: '#e6edf3', gap: '14px',
  });
  bar.innerHTML =
    '<span style="display:flex;gap:7px">' +
      '<i style="width:11px;height:11px;border-radius:50%;background:#ff5f56;display:inline-block"></i>' +
      '<i style="width:11px;height:11px;border-radius:50%;background:#ffbd2e;display:inline-block"></i>' +
      '<i style="width:11px;height:11px;border-radius:50%;background:#27c93f;display:inline-block"></i>' +
    '</span>' +
    '<span style="color:#7c5ced;font-weight:700">EyeBrowse</span>' +
    '<span style="flex:1;background:#0d1117;border:1px solid #30363d;border-radius:7px;padding:6px 12px;' +
      'color:#8b949e;font:13px Consolas,monospace;overflow:hidden;white-space:nowrap">' + url + '</span>';
  const cap = mk('__eb_cap', {
    position: 'fixed', left: '0', right: '0', bottom: '0', zIndex: '2147483647',
    background: 'rgba(13,17,23,0.94)', color: '#e6edf3', boxSizing: 'border-box',
    font: '600 19px "Segoe UI", system-ui, sans-serif', padding: '14px 22px',
    borderTop: '3px solid #7c5ced', letterSpacing: '0.2px',
  });
  cap.innerHTML = '<span style="color:#8b949e">EyeBrowse&nbsp;·&nbsp;</span>' + caption;
}"""


async def _overlay(s, url: str, caption: str) -> None:
    try:
        await s.evaluate(_OVERLAY_JS, {"url": url, "caption": caption})
    except Exception:
        pass


async def main() -> None:
    eb = EyeBrowse()
    video_src = None
    try:
        # Proxyless demo on public sites; fixed viewport → clean 1280x720 frames.
        s = await eb.new_session(record_video=True, no_proxy=True)
        await s.resize(1280, 720)
        video_src = await s.video_path()

        await s.navigate("https://example.com")
        await _overlay(s, "https://example.com",
                       "browser_navigate(url)  —  stealth Chromium · geoip · humanize")
        await asyncio.sleep(2.4)

        await s.navigate("https://en.wikipedia.org/wiki/Web_scraping")
        await _overlay(s, "https://en.wikipedia.org/wiki/Web_scraping",
                       "see any page as an ARIA tree — act by [ref], not pixels")
        await asyncio.sleep(2.4)
        for _ in range(3):
            await s.scroll("down", 520)
            await asyncio.sleep(1.1)
        await _overlay(s, "https://en.wikipedia.org/wiki/Web_scraping",
                       "iframes · shadow DOM · popups · CDP · HAR · captcha · native video")
        await asyncio.sleep(0.6)
        await s.scroll("up", 1000)
        await asyncio.sleep(1.8)

        await eb.close_session(s.id)   # finalizes the .webm
    finally:
        await eb.aclose()

    if video_src and Path(video_src).exists():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(video_src), str(OUT))
        print(f"wrote {OUT}  ({OUT.stat().st_size} bytes)")
        print("convert to GIF:  ffmpeg -i docs/demo.webm docs/demo.gif")
    else:
        print("no video produced — was record_video enabled and the session closed?")


if __name__ == "__main__":
    asyncio.run(main())
