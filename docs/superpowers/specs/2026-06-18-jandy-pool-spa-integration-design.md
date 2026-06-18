# Jandy Pool/Spa — Home Assistant Integration Design

**Date:** 2026-06-18
**Status:** Approved (design phase)

## Purpose

A Home Assistant custom integration (distributed via HACS) that switches a pool
system between **pool** and **SPA** mode. The physical work — actuating two Jandy
valves — is done by a separate Raspberry Pi application that exposes an HTTP API.
This repository contains **only the Home Assistant integration**.

The integration is a thin, stateless mapper over the Pi's HTTP API. The Pi owns
all hardware truth; Home Assistant never assumes state, it reads it.

## Scope

- **In scope:** the HA custom integration (`custom_components/jandy_man/`),
  config flow, polling coordinator, a Select entity (control) and a Sensor entity
  (live status), error handling, tests, and HACS packaging.
- **Out of scope:** the Raspberry Pi application and its valve-control logic
  (exists separately). No MQTT. No authentication (LAN-only deployment).

## System Overview & API Contract

The Pi is reached directly over HTTP on the trusted local network (no auth).

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/status` | — | `200 {"mode": "pool"\|"spa", "moving": true\|false}` |
| `POST` | `/mode` | `{"mode": "pool"\|"spa"}` | `202` (accepted; valves begin moving) |

- `mode` — the committed/target mode.
- `moving` — `true` while the valves are physically rotating, `false` once settled.

This is the agreed contract between the integration and the Pi app. Field/path
names are owned jointly; if the Pi changes them, this document changes with it.

## Home Assistant Components

Custom integration, domain `jandy_man`.

- **API client** (`api.py`) — thin async `aiohttp` wrapper exposing
  `async_get_status()` and `async_set_mode(mode)`. Holds no state.
- **Coordinator** (`coordinator.py`) — a `DataUpdateCoordinator` that polls
  `GET /status`. Adaptive polling interval: slow when idle (~30 s), fast while
  `moving` is `true` (~3 s) so transitions resolve quickly in the UI, then backs
  off once settled.
- **Select** (`select.py`) — options `pool` / `spa`. `current_option` mirrors
  `status.mode`. Selecting an option calls `POST /mode` and then requests an
  immediate coordinator refresh.
- **Sensor** (`sensor.py`) — the live status used by automations:
  `transitioning` when `moving` is `true`, otherwise `pool` / `spa`.
- **Config flow** (`config_flow.py`) — UI setup collecting **host** and **port**.
  Validates the connection by calling `GET /status` once before creating the entry.

## Data Flow

**Command path:**
1. User selects "spa" in the Select entity.
2. Select calls `POST /mode {"mode": "spa"}`.
3. Coordinator performs a forced refresh; polling speeds up.
4. Sensor reports `transitioning` while `/status` returns `moving: true`.
5. When `/status` reports `moving: false`, the Sensor reports `spa` and polling
   backs off to the idle interval.

**State path (including out-of-band changes):**
- The integration never assumes state. If the valves are changed by any other
  means, the next poll of `/status` reflects reality in Home Assistant.

## Error Handling

- **Pi unreachable / timeout:** the coordinator raises `UpdateFailed`; entities
  become **unavailable** (standard HA behavior) and auto-recover on the next
  successful poll.
- **`POST /mode` failure:** raise `HomeAssistantError` so the user sees that the
  command failed. State remains whatever `/status` last reported — no optimistic
  lie.
- **Config-flow validation failure:** show a friendly "cannot connect" error and
  do not create the config entry.

## Repository Structure

Restructure from the current `uv` scaffold to the HACS layout:

```
custom_components/jandy_man/
  __init__.py        # setup/unload entry, create coordinator
  api.py             # async HTTP client
  coordinator.py     # DataUpdateCoordinator, adaptive interval
  config_flow.py     # host + port, validates via /status
  select.py          # pool/spa Select entity
  sensor.py          # live status sensor
  const.py           # domain, defaults, option strings
  manifest.json      # integration manifest
  translations/
    en.json
hacs.json            # HACS metadata (repo root)
```

The existing `main.py` scaffold is removed.

## Testing

- **Framework:** `pytest` + `pytest-homeassistant-custom-component`, with the Pi
  HTTP API mocked (`aioresponses`).
- **Coverage:**
  - Config flow: successful setup and cannot-connect error.
  - Coordinator: `/status` parsing and adaptive interval behavior (fast while
    `moving`, slow when idle).
  - Select: selecting an option issues the correct `POST /mode` call.
  - Sensor: state derivation (`transitioning` / `pool` / `spa`).
  - Error handling: entities go unavailable on poll failure and recover.

## Open Items / Confirmations

- **API contract** (paths and field names in §"System Overview") confirmed with
  the Pi app owner — adjust both sides together if it changes.
- **Domain name `jandy_man`** drives entity IDs (e.g. `select.jandy_man_mode`).
  Rename here if a different domain is preferred.
