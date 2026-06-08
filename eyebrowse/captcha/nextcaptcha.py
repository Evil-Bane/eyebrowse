"""NextCaptcha (https://api.nextcaptcha.com) — Anti-Captcha dialect."""
from __future__ import annotations

from .base import AntiCaptchaStyleSolver


class NextCaptcha(AntiCaptchaStyleSolver):
    name = "nextcaptcha"
    base_url = "https://api.nextcaptcha.com"
    turnstile_type = "TurnstileTaskProxyless"
    recaptcha_type = "RecaptchaV2TaskProxyless"
