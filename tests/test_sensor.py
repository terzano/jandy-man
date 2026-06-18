"""Tests for the Jandy status Sensor entity."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.jandy_man.api import JandyStatus

ENTITY_ID = "sensor.jandy_pool_spa_status"


async def _setup(hass: HomeAssistant, mock_config_entry, status: JandyStatus):
    """Set up the entry with a fixed status."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.jandy_man.JandyApiClient.async_get_status",
        return_value=status,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (JandyStatus(mode="pool", moving=False), "pool"),
        (JandyStatus(mode="spa", moving=False), "spa"),
        (JandyStatus(mode="spa", moving=True), "transitioning"),
    ],
)
async def test_sensor_state_derivation(
    hass: HomeAssistant, mock_config_entry, status, expected
) -> None:
    """moving=True reports transitioning; otherwise the mode."""
    await _setup(hass, mock_config_entry, status)

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == expected
    assert state.attributes["device_class"] == "enum"
    assert state.attributes["options"] == ["pool", "spa", "transitioning"]
