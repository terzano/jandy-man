"""Config flow for the Jandy Pool/Spa integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JandyApiClient, JandyApiError
from .const import DEFAULT_PORT, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class JandyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jandy Pool/Spa."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = JandyApiClient(
                user_input[CONF_HOST], user_input[CONF_PORT], session
            )
            try:
                await client.async_get_status()
            except JandyApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Jandy Pool/Spa", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
