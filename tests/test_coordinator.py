"""Tests for the Jandy data update coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.jandy_man.api import JandyConnectionError, JandyStatus
from custom_components.jandy_man.const import IDLE_INTERVAL, MOVING_INTERVAL
from custom_components.jandy_man.coordinator import JandyCoordinator


def _coordinator(hass: HomeAssistant, mock_config_entry, status_or_error):
    """Build a coordinator with a stubbed client."""
    mock_config_entry.add_to_hass(hass)
    client = AsyncMock()
    if isinstance(status_or_error, Exception):
        client.async_get_status.side_effect = status_or_error
    else:
        client.async_get_status.return_value = status_or_error
    return JandyCoordinator(hass, mock_config_entry, client)


async def test_polls_fast_while_moving(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Interval drops to MOVING_INTERVAL when valves are moving."""
    coordinator = _coordinator(
        hass, mock_config_entry, JandyStatus(mode="spa", moving=True)
    )
    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data == JandyStatus(mode="spa", moving=True)
    assert coordinator.update_interval == timedelta(seconds=MOVING_INTERVAL)


async def test_polls_slow_when_idle(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Interval returns to IDLE_INTERVAL when settled."""
    coordinator = _coordinator(
        hass, mock_config_entry, JandyStatus(mode="pool", moving=False)
    )
    await coordinator.async_refresh()

    assert coordinator.update_interval == timedelta(seconds=IDLE_INTERVAL)


async def test_connection_error_marks_update_failed(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """API errors become UpdateFailed (entities go unavailable)."""
    coordinator = _coordinator(
        hass, mock_config_entry, JandyConnectionError("boom")
    )
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
