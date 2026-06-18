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
