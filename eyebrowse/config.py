"""Settings & secrets for EyeBrowse.

Loaded from environment / ``.env`` via pydantic-settings. Engine + proxy settings use the
``EYEBROWSE_`` prefix; captcha API keys are read under each provider's conventional env var
name (e.g. ``CAPSOLVER_API_KEY``).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EYEBROWSE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,  # allow constructing by field name, not only env alias
    )

    # ── Stealth launch defaults (CloakBrowser — stealth Chromium) ──
    # headful is stealthier; default False (visible). Set EYEBROWSE_HEADLESS=true for headless.
    headless: bool = False
    # Human-like cursor movement (stealth). True = on (CloakBrowser's humanized input), False = off
    # (fastest, least stealthy). A float is accepted for back-compat but coerced to a bool.
    humanize: bool | float = True
    geoip: bool = True
    # Override locale / timezone (e.g. "en-US", "America/New_York"). Leave None to let geoip
    # derive them from the proxy exit IP — the stealthy default.
    locale: str | None = None
    timezone: str | None = None
    # Viewport. Default (None) = maximize to the randomized spoofed screen — keeps full
    # per-session fingerprint entropy while still giving large screenshots. Set both to pin
    # an explicit size (then the screen is forced >= it to stay consistent).
    viewport_width: int | None = None
    viewport_height: int | None = None

    # ── Action / navigation timeouts (ms) ──
    # Cap element actions (click/fill/type/wait_for) SHORT so a blocked action — e.g. a button
    # under a cookie/consent overlay — fails fast and the agent recovers, instead of the 30s
    # Playwright default hanging the run. Navigation keeps a longer budget (page loads on slow/
    # proxied sites need it). Applied at the context level → every page incl. future tabs.
    action_timeout_ms: int = 10000
    navigation_timeout_ms: int = 30000

    # ── Proxy (residential / ISP recommended) ──
    proxy_server: str | None = None
    proxy_username: str | None = None
    proxy_password: str | None = None

    # ── Captcha solver API keys (provider-conventional env names, no prefix) ──
    capsolver_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("CAPSOLVER_API_KEY", "EYEBROWSE_CAPSOLVER_API_KEY")
    )
    twocaptcha_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("TWOCAPTCHA_API_KEY", "EYEBROWSE_TWOCAPTCHA_API_KEY")
    )
    capmonster_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("CAPMONSTER_API_KEY", "EYEBROWSE_CAPMONSTER_API_KEY")
    )
    nextcaptcha_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("NEXTCAPTCHA_API_KEY", "EYEBROWSE_NEXTCAPTCHA_API_KEY")
    )
    captcha_provider: str = "capsolver"

    # ── Runtime data dirs ──
    profiles_dir: str = "profiles"
    data_dir: str = "data"


@lru_cache
def get_settings() -> Settings:
    """Process-wide singleton settings (cached)."""
    return Settings()
