"""Data update coordinator for the Jandy Pool/Spa integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JandyApiClient, JandyApiError, JandyStatus
from .const import DOMAIN, IDLE_INTERVAL, LOGGER, MOVING_INTERVAL


class JandyCoordinator(DataUpdateCoordinator[JandyStatus]):
    """Polls the Pi for status and adapts the polling interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: JandyApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=IDLE_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> JandyStatus:
        """Fetch status and speed up polling while valves are moving."""
        try:
            status = await self.client.async_get_status()
        except JandyApiError as err:
            raise UpdateFailed(f"Error communicating with Jandy API: {err}") from err

        self.update_interval = timedelta(
            seconds=MOVING_INTERVAL if status.moving else IDLE_INTERVAL
        )
        return status
