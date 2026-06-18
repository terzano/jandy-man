"""Tests for the Jandy HTTP API client."""

from __future__ import annotations

import aiohttp
import pytest
from aiohttp.resolver import ThreadedResolver
from aioresponses import aioresponses

from custom_components.jandy_man.api import (
    JandyApiClient,
    JandyConnectionError,
    JandyStatus,
    REQUEST_TIMEOUT,
)


def _make_session() -> aiohttp.ClientSession:
    """Create a ClientSession that avoids spawning background threads."""
    connector = aiohttp.TCPConnector(resolver=ThreadedResolver())
    return aiohttp.ClientSession(connector=connector)


async def test_get_status_parses_response() -> None:
    """It parses mode and moving from /status."""
    with aioresponses() as mock:
        mock.get(
            "http://1.2.3.4:8080/status",
            payload={"mode": "spa", "moving": True},
        )
        session = _make_session()
        client = JandyApiClient("1.2.3.4", 8080, session)
        status = await client.async_get_status()
        await session.close()

    assert status == JandyStatus(mode="spa", moving=True)


async def test_set_mode_posts_payload() -> None:
    """It POSTs the requested mode to /mode."""
    with aioresponses() as mock:
        mock.post("http://1.2.3.4:8080/mode", status=202)
        session = _make_session()
        client = JandyApiClient("1.2.3.4", 8080, session)
        await client.async_set_mode("spa")
        await session.close()

        mock.assert_called_once_with(
            "http://1.2.3.4:8080/mode",
            method="POST",
            json={"mode": "spa"},
            timeout=REQUEST_TIMEOUT,
        )


async def test_get_status_raises_connection_error() -> None:
    """Transport failures surface as JandyConnectionError."""
    with aioresponses() as mock:
        mock.get("http://1.2.3.4:8080/status", exception=aiohttp.ClientError())
        session = _make_session()
        client = JandyApiClient("1.2.3.4", 8080, session)
        with pytest.raises(JandyConnectionError):
            await client.async_get_status()
        await session.close()
