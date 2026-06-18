"""Constants for the Jandy Pool/Spa integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform

DOMAIN = "jandy_man"
LOGGER = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.SENSOR]

DEFAULT_PORT = 8080

MODE_POOL = "pool"
MODE_SPA = "spa"
MODES: list[str] = [MODE_POOL, MODE_SPA]

STATE_TRANSITIONING = "transitioning"

# Polling cadence (seconds): poll fast while valves are physically moving,
# slow once settled.
IDLE_INTERVAL = 30
MOVING_INTERVAL = 3
