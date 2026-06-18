"""Tests for the Jandy config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.jandy_man.api import JandyConnectionError, JandyStatus
from custom_components.jandy_man.const import DOMAIN

USER_INPUT = {CONF_HOST: "1.2.3.4", CONF_PORT: 8080}


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """A reachable controller creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with patch(
        "custom_components.jandy_man.config_flow.JandyApiClient.async_get_status",
        return_value=JandyStatus(mode="pool", moving=False),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == USER_INPUT


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """An unreachable controller shows a cannot_connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.jandy_man.config_flow.JandyApiClient.async_get_status",
        side_effect=JandyConnectionError("boom"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
