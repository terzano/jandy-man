"""Tests for config entry setup and unload."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.jandy_man.api import JandyStatus


async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Entry sets up the coordinator and tears down cleanly."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.jandy_man.JandyApiClient.async_get_status",
        return_value=JandyStatus(mode="pool", moving=False),
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not None

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
