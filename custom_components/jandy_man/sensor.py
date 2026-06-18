"""Sensor entity reporting live pool/spa status."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JandyConfigEntry
from .const import MODES, STATE_TRANSITIONING
from .entity import JandyEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JandyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Jandy status sensor."""
    async_add_entities([JandyStatusSensor(entry.runtime_data, entry)])


class JandyStatusSensor(JandyEntity, SensorEntity):
    """Reports the live valve status: pool, spa, or transitioning."""

    _attr_name = "Status"
    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [*MODES, STATE_TRANSITIONING]

    def __init__(
        self, coordinator, entry: JandyConfigEntry
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def native_value(self) -> str:
        """Return transitioning while moving, else the current mode."""
        data = self.coordinator.data
        return STATE_TRANSITIONING if data.moving else data.mode
