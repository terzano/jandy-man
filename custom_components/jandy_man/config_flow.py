"""Config flow for Jandy Pool/Spa integration (stub — full implementation in a later task)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class JandyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jandy Pool/Spa."""

    VERSION = 1
