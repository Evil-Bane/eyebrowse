"""Captcha solving + TOTP generation (auth gate helpers)."""
from __future__ import annotations

from .. import state


def register(mcp) -> None:
    @mcp.tool()
    async def browser_solve_captcha(
        kind: str = "turnstile",
        website_key: str | None = None,
        provider: str | None = None,
        session_id: str | None = None,
        page_action: str | None = None,
        min_score: float | None = None,
        funcaptcha_subdomain: str | None = None,
        funcaptcha_data: str | None = None,
        timeout: float = 120.0,
    ) -> str:
        """Solve a captcha on the current page and inject the token (no extension).

        kind: 'turnstile' | 'recaptcha_v2' | 'recaptcha_v3' | 'hcaptcha' | 'funcaptcha'.
        website_key is auto-detected from the DOM if omitted (for FunCaptcha that's the
        public key). provider defaults to the configured one (needs that provider's API
        key in the environment). Returns the solved token.

        recaptcha_v3: pass page_action (must match the site's grecaptcha.execute action)
          and optionally min_score (0.1–0.9); the token is injected and grecaptcha.execute
          is overridden to return it.
        funcaptcha (Arkose): funcaptcha_subdomain (the Arkose 'surl') and funcaptcha_data
          (the dynamic 'blob' JSON string) are passed through for sites that require them.
        """
        token = await state.get_engine().solve_captcha(
            session_id=session_id,
            kind=kind,
            website_key=website_key,
            provider=provider,
            page_action=page_action,
            min_score=min_score,
            funcaptcha_subdomain=funcaptcha_subdomain,
            funcaptcha_data=funcaptcha_data,
            timeout=timeout,
        )
        return token

    @mcp.tool()
    async def browser_totp_generate(secret: str, digits: int = 6, interval: int = 30) -> str:
        """Generate a TOTP (time-based one-time password) from a base32 shared secret.

        No browser or session needed — this is a pure computation tool.
        Use it when a site uses an authenticator app (Google Authenticator, Authy, etc.)
        as the second factor. The secret is the base32 string shown during 2FA setup
        (usually labeled 'secret key' or encoded in the QR code's otpauth:// URI).

        digits: code length (default 6). interval: time step in seconds (default 30).
        Returns the current 6-digit (or N-digit) TOTP code as a string.
        """
        try:
            import pyotp
        except ImportError as exc:
            raise RuntimeError(
                "browser_totp_generate requires pyotp. Run: uv add pyotp"
            ) from exc
        code = pyotp.TOTP(secret, digits=digits, interval=interval).now()
        return code
