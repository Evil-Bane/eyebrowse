"""DOM-side captcha helpers: detect the sitekey, inject the solved token.

API-mode bypass: the solver returns a token out-of-band, then we write it into the
hidden response field and override the widget's global getResponse so the page's own
callbacks accept it. Detection + injection are *per captcha kind* — Turnstile, reCAPTCHA
v2/v3, hCaptcha, and FunCaptcha each expose their sitekey and consume their token
differently (see ``solve_captcha`` in api.py for the verified specifics).
"""
from __future__ import annotations

# ── sitekey detection (kind-aware) ───────────────────────────────────────────
# Returns the public sitekey (or, for FunCaptcha, the public key / `pk`) or null.
_DETECT_JS = r"""(kind) => {
  const q = (s) => document.querySelector(s);
  const attr = (el, ...names) => { for (const n of names) { const v = el && el.getAttribute(n); if (v) return v; } return null; };

  if (kind === 'hcaptcha') {
    for (const s of ['.h-captcha[data-sitekey]', '[data-hcaptcha-sitekey]', '[data-sitekey]']) {
      const k = attr(q(s), 'data-sitekey', 'data-hcaptcha-sitekey'); if (k) return k;
    }
    const ifr = q('iframe[src*="hcaptcha.com"]');
    if (ifr) { try { const k = new URL(ifr.src).searchParams.get('sitekey'); if (k) return k; } catch (e) {} }
    return null;
  }

  if (kind === 'recaptcha_v3') {
    // v3 is invisible — the sitekey is the `render=` param of the api.js / enterprise.js script.
    for (const sc of document.querySelectorAll('script[src*="recaptcha/api.js"], script[src*="recaptcha/enterprise.js"]')) {
      try { const k = new URL(sc.src).searchParams.get('render'); if (k && k !== 'explicit') return k; } catch (e) {}
    }
    const k = attr(q('[data-sitekey]'), 'data-sitekey'); if (k) return k;   // rare fallback
    return null;
  }

  if (kind === 'funcaptcha') {
    for (const s of ['[data-pkey]', '[data-public-key]']) {
      const k = attr(q(s), 'data-pkey', 'data-public-key'); if (k) return k;
    }
    // parse pk= out of the pipe-delimited hidden token field if already present
    const ti = q('#verification-token, #FunCaptcha-Token, input[name="fc-token"], #fc-token');
    if (ti && ti.value) { const m = /(?:^|\|)pk=([^|]+)/.exec(ti.value); if (m) return m[1]; }
    // Arkose setup iframe: .../fc/gt2/public_key/<PUBLIC_KEY>
    const ifr = q('iframe[src*="/fc/gt2/public_key/"], iframe[src*="arkoselabs.com"], iframe[src*="funcaptcha.com"]');
    if (ifr) { const m = /public_key\/([^/?#]+)/.exec(ifr.src || ''); if (m) return decodeURIComponent(m[1]); }
    return null;
  }

  // default: Turnstile / reCAPTCHA v2
  for (const s of ['.cf-turnstile[data-sitekey]', '.g-recaptcha[data-sitekey]', '[data-sitekey]', '[data-cf-turnstile-sitekey]']) {
    const k = attr(q(s), 'data-sitekey', 'data-cf-turnstile-sitekey'); if (k) return k;
  }
  const ifr = q('iframe[src*="turnstile"], iframe[src*="recaptcha"]');
  if (ifr) { try { const u = new URL(ifr.src); const k = u.searchParams.get('k') || u.searchParams.get('sitekey'); if (k) return k; } catch (e) {} }
  return null;
}"""

# ── token injection (kind-aware) ─────────────────────────────────────────────
# Two-stage. Stage 1 sets the DOM response field via page.evaluate (reliable everywhere).
# Stage 2 injects a <script> element so the code runs in the PAGE's own world — the reliable
# way to reach the widget globals (grecaptcha/turnstile/hcaptcha/___grecaptcha_cfg) and fire
# the site's data-callback, which page.evaluate's context can't be relied on to touch. That
# callback step is what actually makes callback-gated forms (most modern reCAPTCHA v2) accept
# the token and enable submit.
_INJECT_JS = r"""(args) => {
  const token = args.token, kind = args.kind;
  let n = 0;
  const setVal = (el) => {
    if (!el) return;
    el.value = token;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    n++;
  };
  const fill = (sel) => document.querySelectorAll(sel).forEach(setVal);

  // ── stage 1: response field(s) — plain DOM, settable from the isolated world ──
  if (kind === 'hcaptcha') {
    fill('textarea[name="h-captcha-response"], #h-captcha-response');
    fill('textarea[name="g-recaptcha-response"], #g-recaptcha-response');  // hCaptcha mirrors here
  } else if (kind === 'recaptcha_v3') {
    let ta = document.getElementById('g-recaptcha-response');
    if (!ta) {
      ta = document.createElement('textarea');
      ta.id = 'g-recaptcha-response'; ta.name = 'g-recaptcha-response'; ta.style.display = 'none';
      document.body.appendChild(ta);
    }
    setVal(ta);
  } else if (kind === 'funcaptcha') {
    fill('#verification-token, #FunCaptcha-Token, input[name="fc-token"], #fc-token, input[name="verification-token"]');
  } else {
    fill('[name="cf-turnstile-response"], #cf-turnstile-response');
    fill('[name="g-recaptcha-response"], #g-recaptcha-response');
  }
  if (n === 0) {
    const name = kind === 'hcaptcha' ? 'h-captcha-response'
               : kind === 'recaptcha_v3' ? 'g-recaptcha-response'
               : kind === 'funcaptcha' ? 'fc-token'
               : 'cf-turnstile-response';
    const inp = document.createElement('input');
    inp.type = 'hidden'; inp.name = name; inp.value = token;
    document.body.appendChild(inp);
    n++;
  }

  // ── stage 2: page-world overrides + callback firing (via a <script> in the page world) ──
  try {
    const code =
      '(function(){' +
      '  var T=' + JSON.stringify(token) + ', K=' + JSON.stringify(kind) + ';' +
      '  function fire(cb){ try{ if(typeof cb==="function") cb(T); }catch(e){} }' +
      '  try{ if(typeof grecaptcha!=="undefined"&&grecaptcha){' +
      '    try{ grecaptcha.getResponse=function(){return T;}; }catch(e){}' +
      '    if(grecaptcha.enterprise){ try{ grecaptcha.enterprise.getResponse=function(){return T;}; }catch(e){} }' +
      '    if(K==="recaptcha_v3"){' +
      '      try{ grecaptcha.execute=function(){return Promise.resolve(T);}; }catch(e){}' +
      '      if(grecaptcha.enterprise){ try{ grecaptcha.enterprise.execute=function(){return Promise.resolve(T);}; }catch(e){} } }' +
      '  } }catch(e){}' +
      '  try{ document.querySelectorAll(".g-recaptcha[data-callback],.h-captcha[data-callback],.cf-turnstile[data-callback]").forEach(function(el){' +
      '    var nm=el.getAttribute("data-callback"); if(nm&&typeof window[nm]==="function") fire(window[nm]); }); }catch(e){}' +
      '  try{ var cfg=window.___grecaptcha_cfg; if(cfg&&cfg.clients){ Object.keys(cfg.clients).forEach(function(cid){' +
      '    var c=cfg.clients[cid]||{}; Object.keys(c).forEach(function(k){ var top=c[k];' +
      '      if(top&&typeof top==="object") Object.keys(top).forEach(function(k2){ var o=top[k2];' +
      '        if(o&&typeof o==="object"&&typeof o.callback==="function") fire(o.callback); }); }); }); } }catch(e){}' +
      '  try{ if(typeof hcaptcha!=="undefined"&&hcaptcha) hcaptcha.getResponse=function(){return T;}; }catch(e){}' +
      '  try{ if(typeof turnstile!=="undefined"&&turnstile) turnstile.getResponse=function(){return T;}; }catch(e){}' +
      '})();';
    const s = document.createElement('script');
    s.textContent = code;
    (document.head || document.documentElement).appendChild(s);
    s.remove();
  } catch (e) {}

  return n;
}"""


async def detect_sitekey(page, kind: str = "turnstile") -> str | None:
    """Detect the captcha sitekey on the page for ``kind`` (FunCaptcha → its public key)."""
    return await page.evaluate(_DETECT_JS, kind)


async def inject_token(page, token: str, kind: str = "turnstile") -> int:
    """Inject a solved token into the page for ``kind``; returns how many fields were set."""
    return await page.evaluate(_INJECT_JS, {"token": token, "kind": kind})
