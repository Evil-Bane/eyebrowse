"""CapSolver (https://api.capsolver.com) — Anti-Captcha dialect.

Task-type strings are CapSolver's documented proxyless variants (per the research report).
"""
from __future__ import annotations

from .base import AntiCaptchaStyleSolver


class CapSolver(AntiCaptchaStyleSolver):
    name = "capsolver"
    base_url = "https://api.capsolver.com"
    turnstile_type = "AntiTurnstileTaskProxyLess"
    recaptcha_type = "ReCaptchaV2TaskProxyLess"
    # CapSolver capitalises the "L" in ProxyLess across all its task types.
    hcaptcha_type = "HCaptchaTaskProxyLess"
    recaptcha_v3_type = "ReCaptchaV3TaskProxyLess"
    funcaptcha_type = "FunCaptchaTaskProxyLess"
