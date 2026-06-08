"""Pluggable captcha-solver interface (API-mode only — no browser extension).

A solver browser extension would raise the bot-score (and adds a heavy, fragile dependency),
so EyeBrowse solves purely via provider HTTP APIs and injects the token into the DOM itself
(see ``inject.py``).

CapSolver, 2Captcha (v2 API), CapMonster, and NextCaptcha all speak the Anti-Captcha
``createTask``/``getTaskResult`` JSON dialect, so the polling loop lives once in
:class:`AntiCaptchaStyleSolver`; providers differ only by base URL + task-type names.
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod

import httpx


class CaptchaError(RuntimeError):
    pass


# A normal browser UA — some providers sit behind a WAF that blocks the default httpx UA.
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


class CaptchaSolver(ABC):
    name: str = "base"

    @abstractmethod
    async def solve_turnstile(
        self, *, website_url: str, website_key: str, action: str | None = None,
        cdata: str | None = None, timeout: float = 120.0,
    ) -> str: ...

    @abstractmethod
    async def solve_recaptcha_v2(
        self, *, website_url: str, website_key: str, timeout: float = 120.0,
    ) -> str: ...


class AntiCaptchaStyleSolver(CaptchaSolver):
    base_url: str = ""
    turnstile_type: str = "TurnstileTaskProxyless"
    recaptcha_type: str = "RecaptchaV2TaskProxyless"
    # Anti-Captcha-standard names (used by 2Captcha/NextCaptcha and as defaults); providers
    # override where their string differs (CapSolver uses ...ProxyLess; CapMonster's
    # FunCaptcha is "FunCaptchaTask"). hCaptcha uses the legacy Anti-Captcha-compatible name.
    hcaptcha_type: str = "HCaptchaTaskProxyless"
    recaptcha_v3_type: str = "RecaptchaV3TaskProxyless"
    funcaptcha_type: str = "FunCaptchaTaskProxyless"

    def __init__(self, api_key: str | None, *, base_url: str | None = None, poll_interval: float = 3.0,
                 client: httpx.AsyncClient | None = None):
        if not api_key:
            raise CaptchaError(f"{self.name}: missing API key")
        self.api_key = api_key
        if base_url:
            self.base_url = base_url
        self.poll_interval = poll_interval
        self._client = client

    async def _post(self, client: httpx.AsyncClient, path: str, payload: dict) -> dict:
        # These APIs return their real error as JSON even on non-2xx (e.g. 403 +
        # ERROR_KEY_DOES_NOT_EXIST), so parse the body rather than raising on status.
        resp = await client.post(f"{self.base_url}{path}", json=payload, timeout=30.0)
        try:
            return resp.json()
        except Exception as exc:
            raise CaptchaError(
                f"{self.name} {path}: HTTP {resp.status_code}, non-JSON response: {resp.text[:200]}"
            ) from exc

    async def _solve(self, task: dict, timeout: float) -> str:
        own = self._client is None
        client = self._client or httpx.AsyncClient(headers={"User-Agent": _UA})
        try:
            created = await self._post(client, "/createTask", {"clientKey": self.api_key, "task": task})
            if created.get("errorId"):
                raise CaptchaError(f"{self.name} createTask: {created.get('errorDescription') or created}")
            task_id = created.get("taskId")
            if not task_id:
                raise CaptchaError(f"{self.name}: no taskId in response {created}")

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                await asyncio.sleep(self.poll_interval)
                res = await self._post(client, "/getTaskResult", {"clientKey": self.api_key, "taskId": task_id})
                if res.get("errorId"):
                    raise CaptchaError(f"{self.name} getTaskResult: {res.get('errorDescription') or res}")
                if res.get("status") == "ready":
                    sol = res.get("solution", {}) or {}
                    token = sol.get("token") or sol.get("gRecaptchaResponse")
                    if not token:
                        raise CaptchaError(f"{self.name}: 'ready' but no token in solution {sol}")
                    return token
            raise CaptchaError(f"{self.name}: timed out after {timeout:.0f}s")
        finally:
            if own:
                await client.aclose()

    async def solve_turnstile(self, *, website_url, website_key, action=None, cdata=None, timeout=120.0) -> str:
        task = {"type": self.turnstile_type, "websiteURL": website_url, "websiteKey": website_key}
        if action:
            task["action"] = action
        if cdata:
            task["data"] = cdata
        return await self._solve(task, timeout)

    async def solve_recaptcha_v2(self, *, website_url, website_key, timeout=120.0) -> str:
        task = {"type": self.recaptcha_type, "websiteURL": website_url, "websiteKey": website_key}
        return await self._solve(task, timeout)

    async def solve_hcaptcha(self, *, website_url, website_key, is_invisible=False,
                             data=None, user_agent=None, timeout=120.0) -> str:
        # hCaptcha token lands in solution.gRecaptchaResponse (shared reCAPTCHA schema) or
        # solution.token — _solve() already reads either. `data` = Enterprise rqdata.
        task = {"type": self.hcaptcha_type, "websiteURL": website_url, "websiteKey": website_key}
        if is_invisible:
            task["isInvisible"] = True
        if data:
            task["data"] = data
        if user_agent:
            task["userAgent"] = user_agent
        return await self._solve(task, timeout)

    async def solve_recaptcha_v3(self, *, website_url, website_key, page_action=None,
                                 min_score=None, is_enterprise=False, timeout=120.0) -> str:
        # v3 is score-based/invisible: pageAction must match the site's grecaptcha.execute
        # action, minScore is the trust threshold (0.1–0.9). Token → solution.gRecaptchaResponse.
        task = {"type": self.recaptcha_v3_type, "websiteURL": website_url, "websiteKey": website_key}
        if page_action:
            task["pageAction"] = page_action
        if min_score is not None:
            task["minScore"] = min_score
        if is_enterprise:
            task["isEnterprise"] = True
        return await self._solve(task, timeout)

    async def solve_funcaptcha(self, *, website_url, website_public_key, api_js_subdomain=None,
                               data=None, user_agent=None, timeout=120.0) -> str:
        # Arkose/FunCaptcha: note the param is websitePublicKey (not websiteKey). `data` is the
        # dynamic blob (JSON string) some sites require — it must be captured BEFORE the Arkose
        # iframe loads (loading invalidates it). Token → solution.token.
        task = {"type": self.funcaptcha_type, "websiteURL": website_url,
                "websitePublicKey": website_public_key}
        if api_js_subdomain:
            task["funcaptchaApiJSSubdomain"] = api_js_subdomain
        if data:
            task["data"] = data
        if user_agent:
            task["userAgent"] = user_agent
        return await self._solve(task, timeout)
