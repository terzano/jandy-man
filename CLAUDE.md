# CLAUDE.md — jandy-man (Home Assistant integration)

Custom Home Assistant integration (HACS) that switches a pool between **pool**
and **spa** mode by calling the [`jandy-man-server`](../jandy-man-server) HTTP
API running on an Orange Pi RV2. Domain: `jandy_man`. Python 3.12, managed with `uv`.

Design and implementation docs live in `docs/superpowers/`.

## Architecture decisions

- **Thin, stateless mapper.** The integration only maps HA controls to HTTP
  calls; the Orange Pi owns all hardware truth. HA never assumes state — it reads it.
- **API contract** (shared with the server):
  - `GET /status` → `{"mode": "pool"|"spa", "moving": bool}`
  - `POST /mode` `{"mode": "pool"|"spa"}` → `202` (`409` if already moving)
- **Approach A — the device reports transition.** `/status` exposes a `moving`
  flag; the integration never fakes optimistic state.
- **Entities:** a `Select` (pool/spa control) and an ENUM `Sensor`
  (`pool`/`spa`/`transitioning`), both on one device via the shared
  `JandyEntity` base. A `DataUpdateCoordinator` polls `/status` with an adaptive
  interval — fast (~3 s) while `moving`, slow (~30 s) when idle.
- **Config flow:** host + port only. LAN, no auth by design.
- On API failure the coordinator raises `UpdateFailed` (entities go unavailable);
  a failed command raises `HomeAssistantError` — never a silent optimistic update.

## Conventions

- **Commits:** Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`,
  `test:`, `docs:`, scoped where useful). Keep the `Co-Authored-By` trailer.
- **Branching:** Git Flow — `main` = production, `develop` = integration,
  `feature/*` off `develop` merged back with `--no-ff`, `release/*`/`hotfix/*`
  as needed. Tag releases on `main` (e.g. `v0.1.0`).
- **Imports: RELATIVE.** This is deliberate — HA core, HACS, and
  `hassfest`/lint tooling expect relative imports within a component
  (`from .const import ...`, `from . import JandyConfigEntry`). Do NOT convert
  to absolute. (The server repo uses absolute imports; the rule is "match the
  ecosystem idiom.")

## Testing

- `uv run pytest` — `pytest` + `pytest-homeassistant-custom-component` +
  `aioresponses`. Tests drive real HA machinery (state machine, service
  registry, config-flow engine), not mock internals.
- `tests/conftest.py` forces aiohttp's `ThreadedResolver` (HA's shared session
  uses `AsyncResolver`/pycares, which leaks a daemon thread that trips
  `verify_cleanup`). Keep that fixture.

## Pre-publish TODO

- `custom_components/jandy_man/manifest.json`: replace placeholder `codeowners`
  (`@diego`) and `documentation` URL with the real handle/repo before release.
