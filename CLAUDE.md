# CLAUDE.md — jandy-man (Home Assistant integration)

Custom Home Assistant integration (HACS) that switches a pool between **pool**
and **spa** mode by calling the [`jandy-man-server`](../jandy-man-server) HTTP
API running on an Orange Pi RV2. Domain: `jandy_man`. Python 3.12, managed with `uv`.

Design and implementation docs live in `docs/superpowers/`.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

# Behavioral Guidelines

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**
-> New Feature / "build X": superpowers:brainstorming
-> Bug / error / test failure: superpowers:systematic-debugging
-> Multi-step / 3+ files: superpowers:writing-plans


Before implementing:
- State your assumptions explicitly. Make a reasonable call and document it; ask only when the choice is consequential or you are genuinely blocked.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something critical is unclear and blocks progress, stop, name what's confusing, and ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**
-> Before commit, polish: code-simplifier
-> Dead code / unused exports: code-simplifier

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

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
  `test:`, `docs:`, scoped where useful). Never use `Co-Authored-By` trailer.
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
