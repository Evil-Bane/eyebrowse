"""2Captcha via its Anti-Captcha-compatible v2 API (https://api.2captcha.com)."""
from __future__ import annotations

from .base import AntiCaptchaStyleSolver


class TwoCaptcha(AntiCaptchaStyleSolver):
    name = "twocaptcha"
    base_url = "https://api.2captcha.com"
    turnstile_type = "TurnstileTaskProxyless"
    recaptcha_type = "RecaptchaV2TaskProxyless"
