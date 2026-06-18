# Changelog

All notable changes to EyeBrowse are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.9] — 2026-06-19

### Added
- `eyebrowse` console-script alias (alongside `eyebrowse-mcp`) so `uvx eyebrowse` launches the
  MCP server — matches the identifier used in the official MCP registry listing.

## [0.3.8] — 2026-06-19

### Added
- Listed on the official **MCP registry** (`registry.modelcontextprotocol.io`) as
  `io.github.evil-bane/eyebrowse`. Added an `mcp-name` marker to the package README so the
  registry can verify PyPI package ownership. Metadata only — no code changes.

## [0.3.7] — 2026-06-18

### Added
- `record_video_size` — pin the native recording resolution for `new_session(record_video=True)`
  (and the `browser_new_session` MCP tool via `record_video_width` / `record_video_height`),
  instead of Playwright's 800×450 default. Enables HD (1080p+) session capture from the library
  and over MCP. Threaded through the façade and both engine context paths (ephemeral + persistent).

## [0.3.6] — 2026-06-12

### Changed
- `type_otp` now climbs the DOM to find the whole single-character box group and distributes
  digits across **all N boxes** (previously filled only the first), with a keyboard
  auto-advance fallback.
- `select_combobox` gained a verified click-the-option ladder (native `select` → filter →
  role/menuitem/li/`[class*=option]` by text → keyboard) so it commits on React + overlay
  dropdowns that the one-shot version never selected.

## [0.3.5] — 2026-06-11

### Added
- `browser_find` — locate elements on generic (non-ARIA) snapshot pages.
- `snapshot(enrich=…)` and `wait_for(value=…)` for pages whose ARIA tree is sparse.

## [0.3.4] — 2026-06-11

### Added
- Self-healing interaction verbs and the `select_combobox` / `set_input` / `type_otp`
  primitives.

## [0.3.3] — 2026-06-11

### Fixed
- A `browser_screenshot` return annotation that crashed FastMCP tool registration.

## [0.3.2] — 2026-06-11

### Added
- `browser_screenshot(output_path=…)` writes the PNG to disk and returns the path.

## [0.3.1] — 2026-06-11

### Fixed
- `cdp_click` fast-fails on a stale ref instead of hanging.
- `browser_extract` is gated on the optional `extract` extra (clear error when absent).

## [0.3.0] — 2026-06-10

### Added
- Side-load unpacked Chromium extensions via `new_session(extensions=[…])` (auto-forces a
  persistent, headful context).
- HAR capture verified to work on **persistent** contexts (not just ephemeral), including
  alongside a side-loaded extension.

## [0.2.0] — 2026-06-09

Initial public release — EyeBrowse on the **CloakBrowser** stealth-Chromium engine.

### Added
- Single codebase consumed two ways: a Python library (`from eyebrowse import EyeBrowse`) and
  an **MCP server** (`eyebrowse-mcp`, FastMCP over stdio).
- LLM-drivable interaction model: `aria_snapshot(mode="ai")` → ARIA tree with `[ref=…]`
  handles; act by ref (click / type / hover / select / drag / upload / dialogs / keyboard).
- Full **CDP** surface: trusted cursorless clicks, raw `Network` / `Performance` / `Emulation`,
  MHTML capture, PDF export, and native video.
- Cross-origin iframe routing by ref, shadow-DOM piercing, popup / new-tab switching.
- Stealth defaults (`geoip` + `humanize`), multi-session isolation, proxy + identity rotation.
- API-mode captcha solvers (CapSolver / 2Captcha / CapMonster / NextCaptcha) + TOTP.
- Network inspection / block / mock / offline, cookies + local/session storage CRUD,
  `storage_state`, full **HAR** export, and Crawl4AI markdown extraction (optional extra).

[0.3.9]: https://github.com/Evil-Bane/eyebrowse/compare/v0.3.8...v0.3.9
[0.3.8]: https://github.com/Evil-Bane/eyebrowse/compare/v0.3.7...v0.3.8
[0.3.7]: https://github.com/Evil-Bane/eyebrowse/compare/v0.3.6...v0.3.7
[0.3.6]: https://github.com/Evil-Bane/eyebrowse/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/Evil-Bane/eyebrowse/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/Evil-Bane/eyebrowse/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/Evil-Bane/eyebrowse/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/Evil-Bane/eyebrowse/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Evil-Bane/eyebrowse/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Evil-Bane/eyebrowse/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Evil-Bane/eyebrowse/releases/tag/v0.2.0
