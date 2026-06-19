# Jandy Pool/Spa — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)
[![Validate](https://img.shields.io/github/actions/workflow/status/terzano/jandy-man/validate.yml?branch=main&label=validate&style=flat-square)](https://github.com/terzano/jandy-man/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/terzano/jandy-man?style=flat-square)](https://github.com/terzano/jandy-man/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12%2B-blue.svg?style=flat-square)](https://www.home-assistant.io/)

A custom Home Assistant integration that switches a pool system between **pool**
and **spa** mode by calling an HTTP API on an Orange Pi RV2 that actuates two
Jandy valves. The device side lives in
[jandy-man-server](https://github.com/terzano/jandy-man-server).

## Installation

### HACS

This is a **custom repository** (not in the HACS default store). Add it with one
click:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=terzano&repository=jandy-man&category=integration)

Or add it manually:

1. Install [HACS](https://hacs.xyz/) if you don't have it already.
2. Open HACS in Home Assistant.
3. Open the **⋮** menu (top right) → **Custom repositories**.
4. Add the repository `https://github.com/terzano/jandy-man` with category
   **Integration**.
5. Search for **Jandy Pool/Spa** and click the download button. ⬇️
6. **Restart Home Assistant.**

### Manual

1. Copy `custom_components/jandy_man` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration → Jandy Pool/Spa**.
2. Enter the controller's **host** and **port**.

## Entities

- **Select — Mode:** choose `pool` or `spa`.
- **Sensor — Status:** live valve state (`pool`, `spa`, or `transitioning`).

The integration polls the controller's status, polling faster while the valves
are physically moving and slowing down once they settle.

## Controller API contract

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/status` | — | `{"mode": "pool"\|"spa", "moving": bool}` |
| `POST` | `/mode` | `{"mode": "pool"\|"spa"}` | `202` |
