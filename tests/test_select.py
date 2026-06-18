"""Tests for the Jandy mode Select entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_OPTION, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.jandy_man.api import JandyConnectionError, JandyStatus

ENTITY_ID = "select.jandy_pool_spa_mode"


async def _setup(hass: HomeAssistant, mock_config_entry, set_mode=None):
    """Set up the entry with a stubbed client, SELECT platform only."""
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.jandy_man.PLATFORMS", [Platform.SELECT]
        ),
        patch(
            "custom_components.jandy_man.JandyApiClient.async_get_status",
            return_value=JandyStatus(mode="pool", moving=False),
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Stamp the set_mode mock directly onto the live client instance so it
    # persists beyond the setup patch context for subsequent service calls.
    if set_mode is not None:
        coordinator = mock_config_entry.runtime_data
        coordinator.client.async_set_mode = set_mode


async def test_select_reflects_current_mode(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """current_option mirrors the controller mode."""
    await _setup(hass, mock_config_entry)
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "pool"
    assert state.attributes["options"] == ["pool", "spa"]


async def test_select_option_calls_set_mode(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Selecting an option issues POST /mode for that option."""
    set_mode = AsyncMock()
    await _setup(hass, mock_config_entry, set_mode=set_mode)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: "spa"},
        blocking=True,
    )

    set_mode.assert_awaited_once_with("spa")


async def test_select_option_error_raises(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """A failed command surfaces as HomeAssistantError."""
    set_mode = AsyncMock(side_effect=JandyConnectionError("boom"))
    await _setup(hass, mock_config_entry, set_mode=set_mode)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: "spa"},
            blocking=True,
        )
