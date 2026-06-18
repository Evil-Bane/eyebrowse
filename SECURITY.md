# Security & responsible use

## Responsible use

EyeBrowse drives a real browser with anti-detection features (engine-level fingerprint spoofing,
humanized input, proxy/identity rotation). It is intended for **legitimate, authorized**
automation — testing, accessibility, research, and agents acting on systems you own or are
explicitly permitted to use.

Use it only against sites you own or are authorized to automate, and within their terms of service
and applicable law. The captcha-solving and stealth features exist so that *legitimate* automation
is not false-flagged — they are not a license to bypass access controls, abuse services, or evade
rate limits you are bound by. You are responsible for how you use it.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report privately via GitHub's
[private vulnerability reporting](https://github.com/Evil-Bane/eyebrowse/security/advisories/new)
(Security → Report a vulnerability). Include a description, affected version, and a minimal
reproduction if possible. You'll get an acknowledgement and a fix or mitigation timeline.

## Scope

- **Supported version:** the latest release on [PyPI](https://pypi.org/project/eyebrowse/).
- Secrets (proxy creds, captcha API keys) are read from environment / `.env` and must never be
  committed — `.env` is gitignored; see `.env.example`. EyeBrowse reads **no LLM provider keys**:
  extraction is markdown-only and calls no LLM.
