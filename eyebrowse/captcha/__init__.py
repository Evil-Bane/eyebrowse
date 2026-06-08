"""Captcha solving: pluggable API-mode solvers + DOM detect/inject."""
from __future__ import annotations

from .base import AntiCaptchaStyleSolver, CaptchaError, CaptchaSolver
from .capmonster import CapMonster
from .capsolver import CapSolver
from .inject import detect_sitekey, inject_token
from .nextcaptcha import NextCaptcha
from .twocaptcha import TwoCaptcha

# provider name -> (solver class, settings attribute holding its api key)
_PROVIDERS: dict[str, tuple[type[AntiCaptchaStyleSolver], str]] = {
    "capsolver": (CapSolver, "capsolver_api_key"),
    "twocaptcha": (TwoCaptcha, "twocaptcha_api_key"),
    "capmonster": (CapMonster, "capmonster_api_key"),
    "nextcaptcha": (NextCaptcha, "nextcaptcha_api_key"),
}


def get_solver(name: str | None, settings) -> CaptchaSolver:
    """Build a solver from settings. Falls back to settings.captcha_provider."""
    name = (name or settings.captcha_provider or "capsolver").lower()
    if name not in _PROVIDERS:
        raise CaptchaError(f"Unknown captcha provider {name!r}; choose from {sorted(_PROVIDERS)}")
    cls, attr = _PROVIDERS[name]
    api_key = getattr(settings, attr, None)
    if not api_key:
        raise CaptchaError(f"No API key for {name!r}; set {attr.upper()} in your environment/.env")
    return cls(api_key)


__all__ = [
    "CaptchaError",
    "CaptchaSolver",
    "AntiCaptchaStyleSolver",
    "CapSolver",
    "TwoCaptcha",
    "CapMonster",
    "NextCaptcha",
    "get_solver",
    "detect_sitekey",
    "inject_token",
]
