"""Select entity for switching pool/spa mode."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JandyConfigEntry
from .api import JandyApiError
from .const import MODES
from .coordinator import JandyCoordinator
from .entity import JandyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JandyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Jandy mode select."""
    async_add_entities([JandyModeSelect(entry.runtime_data, entry)])


class JandyModeSelect(JandyEntity, SelectEntity):
    """Select entity that controls pool vs spa mode."""

    _attr_translation_key = "mode"
    _attr_options = MODES

    def __init__(
        self, coordinator: JandyCoordinator, entry: JandyConfigEntry
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_mode"

    @property
    def current_option(self) -> str | None:
        """Return the controller's current mode."""
        return self.coordinator.data.mode

    async def async_select_option(self, option: str) -> None:
        """Command the controller to switch mode."""
        try:
            await self.coordinator.client.async_set_mode(option)
        except JandyApiError as err:
            raise HomeAssistantError(
                f"Failed to set mode to {option}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
