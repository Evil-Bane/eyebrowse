"""CapMonster Cloud (https://api.capmonster.cloud) — Anti-Captcha dialect."""
from __future__ import annotations

from .base import AntiCaptchaStyleSolver


class CapMonster(AntiCaptchaStyleSolver):
    name = "capmonster"
    base_url = "https://api.capmonster.cloud"
    turnstile_type = "TurnstileTaskProxyless"
    recaptcha_type = "RecaptchaV2TaskProxyless"
    # CapMonster's current docs name FunCaptcha "FunCaptchaTask" (no ...Proxyless variant —
    # proxyless is just the type with no proxy fields). hCaptcha + reCAPTCHA-v3 use the
    # Anti-Captcha-compatible base defaults (still accepted by the CapMonster endpoint).
    funcaptcha_type = "FunCaptchaTask"
