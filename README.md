# Jandy Pool/Spa — Home Assistant Integration

A custom Home Assistant integration that switches a pool system between **pool**
and **spa** mode by calling a Raspberry Pi HTTP API which actuates two Jandy valves.

## Installation (HACS)

1. Add this repository as a custom repository in HACS (category: Integration).
2. Install **Jandy Pool/Spa** and restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → Jandy Pool/Spa**.
4. Enter the Raspberry Pi's **host** and **port**.

## Entities

- **Select — Mode:** choose `pool` or `spa`.
- **Sensor — Status:** live valve state (`pool`, `spa`, or `transitioning`).

The integration polls the controller's status, polling faster while the valves
are physically moving and slowing down once they settle.

## Pi API contract

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/status` | — | `{"mode": "pool"\|"spa", "moving": bool}` |
| `POST` | `/mode` | `{"mode": "pool"\|"spa"}` | `202` |
