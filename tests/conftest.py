"""Shared test fixtures for the Jandy Pool/Spa integration."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jandy_man.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Jandy Pool/Spa",
        data={"host": "1.2.3.4", "port": 8080},
    )
