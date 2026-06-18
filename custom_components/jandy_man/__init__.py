"""The Jandy Pool/Spa integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JandyApiClient
from .const import PLATFORMS
from .coordinator import JandyCoordinator

type JandyConfigEntry = ConfigEntry[JandyCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: JandyConfigEntry) -> bool:
    """Set up Jandy Pool/Spa from a config entry."""
    session = async_get_clientsession(hass)
    client = JandyApiClient(entry.data[CONF_HOST], entry.data[CONF_PORT], session)
    coordinator = JandyCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JandyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
