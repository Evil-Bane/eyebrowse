"""ARIA snapshot (ref-annotated) + ref→locator / ref→frame resolution.

Playwright 1.60's ``aria_snapshot(mode="ai")`` yields a YAML ARIA tree with
``[ref=eN]`` handles for top-frame elements and ``[ref=fNeM]`` handles for elements
inside child frames.

IMPORTANT — how the frame prefix actually works (verified against the installed
Playwright 1.60 source, ``coreBundle.js``):

* The ``fN`` prefix is ``"f" + frame.seq`` where ``frame.seq`` is a monotonic counter
  allocated at frame *creation* (``_nextFrameSeq++``). It is **NOT** an index into
  ``page.frames`` (which is depth-first order). On dynamic pages (lazy iframes, ads,
  nested frames) the two diverge, so indexing ``page.frames[N]`` resolves the WRONG
  frame.
* Playwright's own ``aria-ref`` selector engine resolves the frame correctly: given
  ``aria-ref=f1e36`` it runs ``_jumpToAriaRefFrameIfNeeded`` →
  ``frameManager.frames().find(f => f.seq === 1)``. So the right thing to do is hand the
  WHOLE ref (prefix included) to ``page.locator("aria-ref=f1e36")`` and let Playwright
  jump to the frame by seq. That is exactly what :func:`ref_locator` does.
* For a real ``Frame`` object (needed by ``evaluate`` / ``snapshot_frame``) we resolve an
  element via the aria-ref engine and read its ``owner_frame()`` / ``content_frame()`` —
  again never assuming ``page.frames`` order.

Shadow DOM is pierced automatically: the accessibility-tree traversal crosses open
shadow roots, so shadow-hosted elements appear with plain ``eN`` refs and resolve
through the same ``aria-ref=`` engine.
"""
from __future__ import annotations

import re

_REF_TOKEN = re.compile(r"^e\d+$")
# fNeM — an element inside child frame seq N. Playwright's own regex is /^f(\d+)e\d+$/,
# i.e. single-level only (nested frames f1f2eM are NOT supported by the engine either).
_FRAME_ELEMENT_REF = re.compile(r"^f(\d+)e\d+$")
_BARE_FRAME_ID = re.compile(r"^f(\d+)$")


async def aria_ai_snapshot(page_or_frame, *, depth: int | None = None) -> str:
    """Return the ARIA tree with ``[ref=...]`` handles. Accepts a Page or a Frame."""
    kwargs: dict = {"mode": "ai"}
    if depth is not None:
        kwargs["depth"] = depth
    return await page_or_frame.aria_snapshot(**kwargs)


def ref_locator(page, ref: str):
    """Resolve a snapshot reference to a Playwright locator.

    * ``eN``   — top-frame (or shadow-DOM) element → ``page.locator("aria-ref=eN")``.
    * ``fNeM`` — element inside child frame seq N. We pass the FULL ref to the aria-ref
                 engine, which jumps to the owning frame by ``seq`` internally — correct
                 even when ``page.frames`` order differs from seq order.
    * explicit engine selector (``aria-ref=…`` / ``css=…`` / ``xpath=…`` / ``text=…``)
      or a raw CSS selector — passed through unchanged.
    """
    ref = ref.strip()
    if _REF_TOKEN.match(ref) or _FRAME_ELEMENT_REF.match(ref):
        return page.locator(f"aria-ref={ref}")
    return page.locator(ref)


async def frame_for_ref(page, frame_ref: str):
    """Resolve a ``Frame`` object for ``evaluate``/``snapshot_frame`` from a ref.

    Accepts:
    * ``fNeM`` — an element ref *inside* the target frame → that element's ``owner_frame()``.
    * ``eN``   — an ``<iframe>`` element ref → its ``content_frame()`` (or, if ``eN`` is a
                 normal element, its ``owner_frame()``).
    * ``fN``   — a bare frame id → resolved by finding any ``fNe*`` element in the page
                 snapshot and reading its ``owner_frame()``.

    Never indexes ``page.frames`` by N (seq ≠ array index on dynamic pages).
    """
    frame_ref = frame_ref.strip()

    async def _frame_of(element_ref: str):
        handle = await page.locator(f"aria-ref={element_ref}").element_handle()
        if handle is None:
            raise ValueError(f"Could not resolve ref {element_ref!r} to an element.")
        cf = await handle.content_frame()      # ref is an <iframe>/<frame> element
        if cf is not None:
            return cf
        owner = await handle.owner_frame()     # ref is an element inside a frame
        if owner is None:
            raise ValueError(f"ref {element_ref!r} has no owning frame.")
        return owner

    if _FRAME_ELEMENT_REF.match(frame_ref) or _REF_TOKEN.match(frame_ref):
        return await _frame_of(frame_ref)

    m = _BARE_FRAME_ID.match(frame_ref)
    if m:
        snap = await page.aria_snapshot(mode="ai")
        hit = re.search(rf"\[ref=({re.escape(frame_ref)}e\d+)\]", snap)
        if not hit:
            raise ValueError(
                f"No elements found for frame {frame_ref!r} in the current snapshot "
                f"(the frame may be empty or not loaded yet — try wait_for(network_idle) "
                f"then retry, or pass an element ref inside the frame like '{frame_ref}e5')."
            )
        return await _frame_of(hit.group(1))

    raise ValueError(
        f"frame_ref must be 'fN' (frame id), 'fNeM' (element in frame), or 'eN' "
        f"(an <iframe> element ref); got {frame_ref!r}."
    )


def frame_prefix_for(frame_ref: str) -> str | None:
    """The ``fN`` prefix to make a frame-local ``eM`` ref actionable, if derivable
    directly from ``frame_ref`` (``fN`` or ``fNeM``). Returns None for an ``eN`` iframe
    ref (seq not knowable from the input alone)."""
    frame_ref = frame_ref.strip()
    m = _FRAME_ELEMENT_REF.match(frame_ref) or _BARE_FRAME_ID.match(frame_ref)
    return f"f{m.group(1)}" if m else None


async def discover_frame_prefix(page, frame) -> str | None:
    """Best-effort: find the ``fN`` prefix Playwright assigned to ``frame`` by scanning
    the page snapshot and matching ``owner_frame()`` (used when only an ``<iframe>``
    element ref was given). Returns None if it can't be determined."""
    snap = await page.aria_snapshot(mode="ai")
    seen: set[str] = set()
    for pf in re.findall(r"\[ref=(f\d+)e\d+\]", snap):
        if pf in seen:
            continue
        seen.add(pf)
        hit = re.search(rf"\[ref=({re.escape(pf)}e\d+)\]", snap)
        if not hit:
            continue
        handle = await page.locator(f"aria-ref={hit.group(1)}").element_handle()
        if handle is None:
            continue
        owner = await handle.owner_frame()
        if owner == frame:
            return pf
    return None
