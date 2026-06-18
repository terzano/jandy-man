"""Shared test fixtures for the Jandy Pool/Spa integration."""

from __future__ import annotations

import homeassistant.helpers.aiohttp_client as ha_aiohttp_client
import pytest
from aiohttp.resolver import ThreadedResolver
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jandy_man.const import DOMAIN


@pytest.fixture(autouse=True)
def force_threaded_resolver(monkeypatch: pytest.MonkeyPatch):
    """Use aiohttp's ThreadedResolver instead of the aiodns/pycares AsyncResolver.

    HA's ``_async_get_connector`` builds the shared client session with an
    ``AsyncResolver``. When pycares is installed, that spawns a daemon thread
    (``_run_safe_shutdown_loop``) the first time the session is created, which
    outlives the test and trips the ``verify_cleanup`` fixture. ThreadedResolver
    uses the event loop's default executor, which the cleanup fixture shuts
    down, so no thread is left behind.
    """
    monkeypatch.setattr(ha_aiohttp_client, "AsyncResolver", ThreadedResolver)
    yield


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
