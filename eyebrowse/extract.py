"""Extraction via Crawl4AI's ``raw:`` HTML-feed pattern — **markdown only, no LLM**.

EyeBrowse does the stealthy navigation/rendering; we hand the rendered HTML
(``page.content()``) to Crawl4AI as ``raw:<html>`` so it skips its own browser and runs
just its markdown pipeline — the raw feed is the integration point, so Crawl4AI never
launches a second (non-stealth) browser.

No LLM is involved: the agent consuming EyeBrowse is itself the LLM and reasons over the
returned markdown. (We deliberately do NOT call any LLM provider here — that would mean
silently using the user's API keys.)

Crawl4AI is an optional dependency (``uv sync --extra extract``); imports are lazy so the
core engine works without it.
"""
from __future__ import annotations


def _raw_url(raw_html: str) -> str:
    return f"raw:{raw_html}"


async def to_markdown(crawler, raw_html: str, *, threshold: float = 0.48, fit: bool = True) -> str:
    """Rendered HTML -> clean, token-efficient markdown (pruned)."""
    from crawl4ai import CacheMode, CrawlerRunConfig, DefaultMarkdownGenerator, PruningContentFilter

    md_gen = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=threshold, threshold_type="fixed")
    )
    cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, markdown_generator=md_gen)
    result = await crawler.arun(url=_raw_url(raw_html), config=cfg)
    if not result.success:
        raise RuntimeError(f"Crawl4AI markdown generation failed: {result.error_message}")
    md = result.markdown
    if fit:
        fit_md = getattr(md, "fit_markdown", None)
        if fit_md:
            return fit_md
    return getattr(md, "raw_markdown", None) or str(md)
