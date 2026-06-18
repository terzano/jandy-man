# Jandy Pool/Spa Home Assistant Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS-distributable Home Assistant custom integration (`jandy_man`) that switches a pool system between `pool` and `spa` mode by calling a Raspberry Pi HTTP API, exposing a Select (control) and a Sensor (live status).

**Architecture:** A thin, stateless mapper over the Pi's HTTP API. An async `aiohttp` client wraps `GET /status` and `POST /mode`. A `DataUpdateCoordinator` polls `/status` with an adaptive interval (fast while valves are `moving`, slow when idle). A Select entity issues mode commands; a Sensor entity reports live status (`pool` / `spa` / `transitioning`). The Pi owns all hardware truth — HA never assumes state, it reads it.

**Tech Stack:** Python 3.12, Home Assistant custom integration, `aiohttp`, `voluptuous`; tested with `pytest` + `pytest-homeassistant-custom-component` + `aioresponses`.

**API contract (confirmed):**
| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/status` | — | `200 {"mode": "pool"\|"spa", "moving": true\|false}` |
| `POST` | `/mode` | `{"mode": "pool"\|"spa"}` | `202` |

---

## File Structure

```
custom_components/jandy_man/
  __init__.py        # config-entry setup/unload; builds client + coordinator, stores on runtime_data
  api.py             # JandyApiClient + JandyStatus dataclass + error types
  coordinator.py     # JandyCoordinator: polls /status, adaptive interval
  config_flow.py     # host + port form, validates via /status
  select.py          # JandyModeSelect (pool/spa control)
  sensor.py          # JandyStatusSensor (pool/spa/transitioning)
  const.py           # DOMAIN, LOGGER, PLATFORMS, modes, intervals
  manifest.json      # integration manifest
  translations/en.json
hacs.json            # HACS metadata (repo root)
tests/
  conftest.py        # enable custom integrations + shared fixtures
  test_api.py
  test_coordinator.py
  test_config_flow.py
  test_init.py
  test_select.py
  test_sensor.py
```

Each module has one responsibility. `api.py` owns transport + parsing; `coordinator.py` owns polling cadence; entities own HA presentation; `config_flow.py` owns setup UX. They depend only downward (entities → coordinator → api).

---

## Task 1: Project scaffolding, packaging, and constants

**Files:**
- Delete: `main.py`
- Create: `custom_components/jandy_man/__init__.py` (empty placeholder, filled in Task 4)
- Create: `custom_components/jandy_man/const.py`
- Create: `custom_components/jandy_man/manifest.json`
- Create: `hacs.json`
- Create: `tests/conftest.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove the scaffold entrypoint**

```bash
git rm main.py
```

- [ ] **Step 2: Write `custom_components/jandy_man/const.py`**

```python
"""Constants for the Jandy Pool/Spa integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform

DOMAIN = "jandy_man"
LOGGER = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.SENSOR]

DEFAULT_PORT = 8080

MODE_POOL = "pool"
MODE_SPA = "spa"
MODES: list[str] = [MODE_POOL, MODE_SPA]

STATE_TRANSITIONING = "transitioning"

# Polling cadence (seconds): poll fast while valves are physically moving,
# slow once settled.
IDLE_INTERVAL = 30
MOVING_INTERVAL = 3
```

- [ ] **Step 3: Write `custom_components/jandy_man/manifest.json`**

```json
{
  "domain": "jandy_man",
  "name": "Jandy Pool/Spa",
  "codeowners": ["@diego"],
  "config_flow": true,
  "documentation": "https://github.com/diego/jandy-man",
  "integration_type": "device",
  "iot_class": "local_polling",
  "requirements": [],
  "version": "0.1.0"
}
```

- [ ] **Step 4: Write `hacs.json` at the repo root**

```json
{
  "name": "Jandy Pool/Spa",
  "render_readme": true,
  "homeassistant": "2024.12.0"
}
```

- [ ] **Step 5: Create an empty `custom_components/jandy_man/__init__.py`**

```python
"""The Jandy Pool/Spa integration."""
```

- [ ] **Step 6: Replace `pyproject.toml` with dev dependencies and pytest config**

```toml
[project]
name = "jandy-man"
version = "0.1.0"
description = "Home Assistant custom integration to switch a pool between pool and spa mode via a Raspberry Pi HTTP API."
readme = "README.md"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = [
    "homeassistant>=2024.12.0",
    "pytest>=8.0",
    "pytest-homeassistant-custom-component>=0.13.0",
    "aioresponses>=0.7.6",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 7: Write `tests/conftest.py`**

```python
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
```

- [ ] **Step 8: Install dependencies and confirm pytest collects**

Run: `uv sync && uv run pytest -q`
Expected: collection succeeds with "no tests ran" (exit code 5) — environment is wired up. If `uv` is unavailable, use `pip install -e . --group dev` then `pytest -q`.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "chore: scaffold jandy_man custom integration packaging"
```

---

## Task 2: API client and status model

**Files:**
- Create: `custom_components/jandy_man/api.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the Jandy HTTP API client."""

from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.jandy_man.api import (
    JandyApiClient,
    JandyConnectionError,
    JandyStatus,
)


async def test_get_status_parses_response() -> None:
    """It parses mode and moving from /status."""
    with aioresponses() as mock:
        mock.get(
            "http://1.2.3.4:8080/status",
            payload={"mode": "spa", "moving": True},
        )
        async with aiohttp.ClientSession() as session:
            client = JandyApiClient("1.2.3.4", 8080, session)
            status = await client.async_get_status()

    assert status == JandyStatus(mode="spa", moving=True)


async def test_set_mode_posts_payload() -> None:
    """It POSTs the requested mode to /mode."""
    with aioresponses() as mock:
        mock.post("http://1.2.3.4:8080/mode", status=202)
        async with aiohttp.ClientSession() as session:
            client = JandyApiClient("1.2.3.4", 8080, session)
            await client.async_set_mode("spa")

        mock.assert_called_once_with(
            "http://1.2.3.4:8080/mode", method="POST", json={"mode": "spa"}
        )


async def test_get_status_raises_connection_error() -> None:
    """Transport failures surface as JandyConnectionError."""
    with aioresponses() as mock:
        mock.get("http://1.2.3.4:8080/status", exception=aiohttp.ClientError())
        async with aiohttp.ClientSession() as session:
            client = JandyApiClient("1.2.3.4", 8080, session)
            with pytest.raises(JandyConnectionError):
                await client.async_get_status()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.jandy_man.api'`

- [ ] **Step 3: Write `custom_components/jandy_man/api.py`**

```python
"""HTTP client for the Raspberry Pi Jandy controller."""

from __future__ import annotations

from dataclasses import dataclass

import aiohttp

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


@dataclass(frozen=True)
class JandyStatus:
    """Snapshot of the controller state."""

    mode: str
    moving: bool


class JandyApiError(Exception):
    """Base error for the Jandy API."""


class JandyConnectionError(JandyApiError):
    """Raised when the controller cannot be reached."""


class JandyApiClient:
    """Thin async wrapper over the Pi's HTTP API."""

    def __init__(
        self, host: str, port: int, session: aiohttp.ClientSession
    ) -> None:
        """Initialize the client."""
        self._base_url = f"http://{host}:{port}"
        self._session = session

    async def async_get_status(self) -> JandyStatus:
        """Fetch the current mode and movement state."""
        try:
            async with self._session.get(
                f"{self._base_url}/status", timeout=REQUEST_TIMEOUT
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError as err:
            raise JandyConnectionError(str(err)) from err
        return JandyStatus(mode=data["mode"], moving=bool(data["moving"]))

    async def async_set_mode(self, mode: str) -> None:
        """Command the controller to switch to the given mode."""
        try:
            async with self._session.post(
                f"{self._base_url}/mode",
                json={"mode": mode},
                timeout=REQUEST_TIMEOUT,
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as err:
            raise JandyConnectionError(str(err)) from err
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/jandy_man/api.py tests/test_api.py
git commit -m "feat: add Jandy HTTP API client and status model"
```

---

## Task 3: Polling coordinator with adaptive interval

**Files:**
- Create: `custom_components/jandy_man/coordinator.py`
- Test: `tests/test_coordinator.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_coordinator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.jandy_man.coordinator'`

- [ ] **Step 3: Write `custom_components/jandy_man/coordinator.py`**

```python
"""Data update coordinator for the Jandy Pool/Spa integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JandyApiClient, JandyApiError, JandyStatus
from .const import DOMAIN, IDLE_INTERVAL, LOGGER, MOVING_INTERVAL


class JandyCoordinator(DataUpdateCoordinator[JandyStatus]):
    """Polls the Pi for status and adapts the polling interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: JandyApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=IDLE_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> JandyStatus:
        """Fetch status and speed up polling while valves are moving."""
        try:
            status = await self.client.async_get_status()
        except JandyApiError as err:
            raise UpdateFailed(f"Error communicating with Jandy API: {err}") from err

        self.update_interval = timedelta(
            seconds=MOVING_INTERVAL if status.moving else IDLE_INTERVAL
        )
        return status
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_coordinator.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/jandy_man/coordinator.py tests/test_coordinator.py
git commit -m "feat: add polling coordinator with adaptive interval"
```

---

## Task 4: Config-entry setup and unload

**Files:**
- Modify: `custom_components/jandy_man/__init__.py`
- Test: `tests/test_init.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_init.py -v`
Expected: FAIL — setup returns False / `runtime_data` is None (no platforms wired up yet)

- [ ] **Step 3: Write `custom_components/jandy_man/__init__.py`**

```python
"""The Jandy Pool/Spa integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JandyApiClient
from .const import PLATFORMS
from .coordinator import JandyCoordinator

type JandyConfigEntry = ConfigEntry[JandyCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: JandyConfigEntry) -> bool:
    """Set up Jandy Pool/Spa from a config entry."""
    session = async_get_clientsession(hass)
    client = JandyApiClient(entry.data[CONF_HOST], entry.data[CONF_PORT], session)
    coordinator = JandyCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JandyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

Note: `select.py` and `sensor.py` (Tasks 6 & 7) must exist for `async_forward_entry_setups` to succeed. Until then this test fails at the forward step — that is expected; it passes once Tasks 6 & 7 are done. Run this test again at the end of Task 7.

- [ ] **Step 4: Commit**

```bash
git add custom_components/jandy_man/__init__.py tests/test_init.py
git commit -m "feat: wire up config entry setup and unload"
```

---

## Task 5: Config flow (host + port)

**Files:**
- Create: `custom_components/jandy_man/config_flow.py`
- Test: `tests/test_config_flow.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config_flow.py -v`
Expected: FAIL — config flow handler not found / `ModuleNotFoundError`

- [ ] **Step 3: Write `custom_components/jandy_man/config_flow.py`**

```python
"""Config flow for the Jandy Pool/Spa integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JandyApiClient, JandyApiError
from .const import DEFAULT_PORT, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class JandyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jandy Pool/Spa."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = JandyApiClient(
                user_input[CONF_HOST], user_input[CONF_PORT], session
            )
            try:
                await client.async_get_status()
            except JandyApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="Jandy Pool/Spa", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config_flow.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/jandy_man/config_flow.py tests/test_config_flow.py
git commit -m "feat: add config flow with host/port and connectivity check"
```

---

## Task 6: Select entity (pool/spa control)

**Files:**
- Create: `custom_components/jandy_man/select.py`
- Test: `tests/test_select.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the Jandy mode Select entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_OPTION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.jandy_man.api import JandyConnectionError, JandyStatus

ENTITY_ID = "select.jandy_pool_spa_mode"


async def _setup(hass: HomeAssistant, mock_config_entry, set_mode=None):
    """Set up the entry with a stubbed client."""
    mock_config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.jandy_man.JandyApiClient.async_get_status",
            return_value=JandyStatus(mode="pool", moving=False),
        ),
        patch(
            "custom_components.jandy_man.JandyApiClient.async_set_mode",
            new=set_mode or AsyncMock(),
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_select.py -v`
Expected: FAIL — entity does not exist (`state is None`) / `ModuleNotFoundError`

- [ ] **Step 3: Write `custom_components/jandy_man/select.py`**

```python
"""Select entity for switching pool/spa mode."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import JandyConfigEntry
from .api import JandyApiError
from .const import MODES
from .coordinator import JandyCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JandyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Jandy mode select."""
    async_add_entities([JandyModeSelect(entry.runtime_data, entry)])


class JandyModeSelect(CoordinatorEntity[JandyCoordinator], SelectEntity):
    """Select entity that controls pool vs spa mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "mode"
    _attr_options = MODES

    def __init__(
        self, coordinator: JandyCoordinator, entry: JandyConfigEntry
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_select.py -v`
Expected: PASS (3 passed)

Note: the entity id `select.jandy_pool_spa_mode` derives from the entry title "Jandy Pool/Spa" + translation key "mode". If HA's slug differs, adjust `ENTITY_ID` in the test to the value shown by `hass.states.async_entity_ids()`.

- [ ] **Step 5: Commit**

```bash
git add custom_components/jandy_man/select.py tests/test_select.py
git commit -m "feat: add pool/spa mode select entity"
```

---

## Task 7: Sensor entity (live status)

**Files:**
- Create: `custom_components/jandy_man/sensor.py`
- Test: `tests/test_sensor.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_sensor.py -v`
Expected: FAIL — entity does not exist (`state is None`) / `ModuleNotFoundError`

- [ ] **Step 3: Write `custom_components/jandy_man/sensor.py`**

```python
"""Sensor entity reporting live pool/spa status."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import JandyConfigEntry
from .const import MODES, STATE_TRANSITIONING
from .coordinator import JandyCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JandyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Jandy status sensor."""
    async_add_entities([JandyStatusSensor(entry.runtime_data, entry)])


class JandyStatusSensor(CoordinatorEntity[JandyCoordinator], SensorEntity):
    """Reports the live valve status: pool, spa, or transitioning."""

    _attr_has_entity_name = True
    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [*MODES, STATE_TRANSITIONING]

    def __init__(
        self, coordinator: JandyCoordinator, entry: JandyConfigEntry
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def native_value(self) -> str:
        """Return transitioning while moving, else the current mode."""
        data = self.coordinator.data
        return STATE_TRANSITIONING if data.moving else data.mode
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_sensor.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Re-run the init test now that both platforms exist**

Run: `uv run pytest tests/test_init.py -v`
Expected: PASS (1 passed) — `async_forward_entry_setups` now succeeds.

- [ ] **Step 6: Commit**

```bash
git add custom_components/jandy_man/sensor.py tests/test_sensor.py
git commit -m "feat: add live status sensor (pool/spa/transitioning)"
```

---

## Task 8: Translations and full verification

**Files:**
- Create: `custom_components/jandy_man/translations/en.json`

- [ ] **Step 1: Write `custom_components/jandy_man/translations/en.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to Jandy controller",
        "data": {
          "host": "Host",
          "port": "Port"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect to the Jandy controller."
    }
  },
  "entity": {
    "select": {
      "mode": {
        "name": "Mode"
      }
    },
    "sensor": {
      "status": {
        "name": "Status",
        "state": {
          "pool": "Pool",
          "spa": "Spa",
          "transitioning": "Transitioning"
        }
      }
    }
  }
}
```

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS — all tests across api, coordinator, init, config_flow, select, sensor (15 passed).

- [ ] **Step 3: Write a short README for HACS**

Replace the empty `README.md` with install + usage notes:

```markdown
# Jandy Pool/Spa — Home Assistant Integration

A custom Home Assistant integration that switches a pool system between **pool**
and **spa** mode by calling a Raspberry Pi HTTP API which actuates two Jandy valves.

## Installation (HACS)

1. Add this repository as a custom repository in HACS (category: Integration).
2. Install **Jandy Pool/Spa** and restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → Jandy Pool/Spa**.
4. Enter the Raspberry Pi's **host** and **port**.

## Entities

- **Select — Mode:** choose `pool` or `spa`.
- **Sensor — Status:** live valve state (`pool`, `spa`, or `transitioning`).

## Pi API contract

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/status` | — | `{"mode": "pool"\|"spa", "moving": bool}` |
| `POST` | `/mode` | `{"mode": "pool"\|"spa"}` | `202` |
```

- [ ] **Step 4: Commit**

```bash
git add custom_components/jandy_man/translations/en.json README.md
git commit -m "feat: add translations and HACS README"
```

---

## Self-Review Notes

- **Spec coverage:** API client + contract (Task 2) ✓; adaptive polling coordinator (Task 3) ✓; Select control (Task 6) ✓; status Sensor with `transitioning` (Task 7) ✓; config flow host+port + cannot-connect (Task 5) ✓; entities unavailable on error (Task 3 `UpdateFailed`) ✓; HACS layout + `main.py` removal (Task 1) ✓; full test matrix (Task 8) ✓.
- **Type consistency:** `JandyStatus(mode, moving)`, `JandyApiClient.async_get_status/async_set_mode`, `JandyCoordinator.client`, `entry.runtime_data` (a `JandyCoordinator`), and constants `MODES` / `STATE_TRANSITIONING` / `IDLE_INTERVAL` / `MOVING_INTERVAL` are referenced identically across all tasks.
- **Known follow-up:** `manifest.json` `codeowners`/`documentation` use `@diego` / the repo URL — update to the real GitHub handle and repo before publishing. Entity-id slugs in Task 6/7 tests depend on the entry title; the notes explain how to adjust if HA slugs differently.
```
