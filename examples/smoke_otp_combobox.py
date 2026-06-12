"""Smoke test for the two engine fixes in 0.3.6:
  - type_otp now distributes a code across ALL N single-char auto-advance boxes
    (old version only filled box 1 when each box sat in its own wrapper).
  - select_combobox now COMMITS on a custom listbox via the click-the-option rung
    (old version reported committed=False and never selected).

Run:  uv run python examples/smoke_otp_combobox.py
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from eyebrowse import EyeBrowse

# 6 single-char boxes, EACH in its own <span> wrapper (so box1.parentElement holds box1
# alone — the exact shape that defeated the old type_otp). Auto-advance on input.
OTP_HTML = """<!doctype html><html><head><meta charset='utf-8'><title>otp</title></head>
<body><h1>Enter code</h1><div id='otp'>
<span><input id='d1' maxlength='1' aria-label='digit 1'></span>
<span><input id='d2' maxlength='1'></span>
<span><input id='d3' maxlength='1'></span>
<span><input id='d4' maxlength='1'></span>
<span><input id='d5' maxlength='1'></span>
<span><input id='d6' maxlength='1'></span>
</div>
<script>
document.querySelectorAll('#otp input').forEach((b, i, all) => {
  b.addEventListener('input', () => { if (b.value && all[i+1]) all[i+1].focus(); });
});
</script></body></html>
"""

# Custom combobox: a role=combobox trigger + a role=listbox of role=option items.
# No native <select>, no search input — keyboard ArrowDown+Enter does nothing here, so the
# old one-shot version returned committed=False. The new click-the-option rung commits.
COMBO_HTML = """<!doctype html><html><head><meta charset='utf-8'><title>combo</title></head>
<body><h1>Pick country</h1>
<div id='cc' role='combobox' aria-label='country' tabindex='0'>Select country</div>
<ul id='list' role='listbox' style='display:none'>
  <li role='option'>France</li>
  <li role='option'>Germany</li>
  <li role='option'>Spain</li>
  <li role='option'>Ukraine</li>
</ul>
<script>
const cc = document.getElementById('cc'), list = document.getElementById('list');
cc.addEventListener('click', () => { list.style.display = list.style.display === 'none' ? 'block' : 'none'; });
list.querySelectorAll('[role=option]').forEach(o => {
  o.addEventListener('click', () => { cc.textContent = o.textContent; list.style.display = 'none'; });
});
</script></body></html>
"""


async def main() -> None:
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    otp_file = data_dir / "smoke_otp.html"
    combo_file = data_dir / "smoke_combo.html"
    otp_file.write_text(OTP_HTML, encoding="utf-8")
    combo_file.write_text(COMBO_HTML, encoding="utf-8")

    ok = True
    eb = EyeBrowse()
    try:
        async with eb.session(headless=True, geoip=False, humanize=False) as s:
            # --- type_otp across 6 boxes ---
            await s.navigate(otp_file.resolve().as_uri())
            res = await s.type_otp("css=#d1", "123456")
            print(f"type_otp -> {res}")
            vals = await s.evaluate(
                "() => Array.from(document.querySelectorAll('#otp input')).map(i => i.value).join('')"
            )
            print(f"boxes now hold -> {vals!r}")
            if vals != "123456":
                ok = False
                print("  !! FAIL: expected all 6 boxes to read '123456'")
            else:
                print("  OK: all 6 boxes filled")

            # --- select_combobox commit ---
            await s.navigate(combo_file.resolve().as_uri())
            res = await s.select_combobox("css=#cc", "Germany")
            print(f"select_combobox -> {res}")
            shown = await s.evaluate("() => document.getElementById('cc').textContent")
            print(f"trigger now shows -> {shown!r}")
            if not (res.get("committed") and shown == "Germany"):
                ok = False
                print("  !! FAIL: combobox did not commit to 'Germany'")
            else:
                print("  OK: combobox committed to Germany")
    finally:
        await eb.aclose()

    print("\nSMOKE_OK" if ok else "\nSMOKE_FAIL")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
