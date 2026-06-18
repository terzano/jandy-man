"""Base entity for the Jandy Pool/Spa integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import JandyConfigEntry
from .const import DOMAIN
from .coordinator import JandyCoordinator


class JandyEntity(CoordinatorEntity[JandyCoordinator]):
    """Base entity tying all Jandy entities to one device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: JandyCoordinator, entry: JandyConfigEntry
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
        )
