"""Tests of the initialization of the nefiteasy integration."""

import asyncio
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import ClientMock

entry_data = {
    "serial": "123456789",
    "accesskey": "myAccessKey",
    "password": "myPass",
    "min_temp": 10,
    "max_temp": 28,
    "temp_step": 0.5,
    "name": "Nefit",
}


@patch("custom_components.nefiteasy.NefitCore")
async def test_load_unload_entry(mock_class, hass: HomeAssistant):
    """Validate that setup entry also configure the client."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    config_entry = MockConfigEntry(domain="nefiteasy", data=entry_data)

    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == config_entries.ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == config_entries.ConfigEntryState.NOT_LOADED


@patch("custom_components.nefiteasy.NefitCore")
async def test_setup_connection_fail_timeout(mock_class, hass: HomeAssistant):
    """Test setup connection with timeout failure."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    config_entry = MockConfigEntry(domain="nefiteasy", data=entry_data)

    config_entry.add_to_hass(hass)

    async def wait():
        raise asyncio.TimeoutError

    client.xmppclient.connected_event.wait = wait

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == config_entries.ConfigEntryState.SETUP_RETRY


@patch("custom_components.nefiteasy.NefitCore")
async def test_setup_validation_fail_timeout(mock_class, hass: HomeAssistant):
    """Test setup with validation timeout."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    config_entry = MockConfigEntry(domain="nefiteasy", data=entry_data)

    config_entry.add_to_hass(hass)

    async def wait():
        raise asyncio.TimeoutError

    client.xmppclient.message_event.wait = wait

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == config_entries.ConfigEntryState.SETUP_RETRY


@patch("custom_components.nefiteasy.NefitCore")
async def test_connect_clears_stale_events(mock_class, hass: HomeAssistant):
    """Test that stale events from a previous session are cleared before connect."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    # Pre-set stale events as if left over from a previous session
    client.xmppclient.connected_event.set()
    client.xmppclient.message_event.set()

    # Reconnect fails to produce new handshake event
    async def fake_connect():
        pass

    async def timeout_wait():
        raise asyncio.TimeoutError

    client.connect = fake_connect
    client.xmppclient.connected_event.wait = timeout_wait

    config_entry = MockConfigEntry(domain="nefiteasy", data=entry_data)
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == config_entries.ConfigEntryState.SETUP_RETRY


@patch("custom_components.nefiteasy.NefitCore")
async def test_duplicate_session_end_suppression(mock_class, hass: HomeAssistant):
    """Test that duplicate unexpected session_end calls only schedule a single refresh."""
    from custom_components.nefiteasy.const import STATE_CONNECTION_VERIFIED, STATE_INIT

    client = ClientMock(mock_class)
    mock_class.return_value = client

    config_entry = MockConfigEntry(domain="nefiteasy", data=entry_data)
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data["nefiteasy"][config_entry.entry_id]["client"]
    assert coordinator.connected_state == STATE_CONNECTION_VERIFIED

    with patch.object(coordinator, "async_refresh") as mock_refresh:
        # First unexpected disconnect
        await coordinator.session_end_callback()
        assert coordinator.connected_state == STATE_INIT
        assert mock_refresh.call_count == 1

        # Duplicate unexpected disconnect arriving immediately after
        await coordinator.session_end_callback()
        assert mock_refresh.call_count == 1


@patch("custom_components.nefiteasy.NefitCore")
async def test_connect_cancellation_resets_is_connecting(
    mock_class, hass: HomeAssistant
):
    """Test that cancellation during connect resets is_connecting."""
    import pytest

    from custom_components.nefiteasy import NefitEasy

    client = ClientMock(mock_class)
    mock_class.return_value = client

    coordinator = NefitEasy(hass, entry_data)

    async def cancelled_wait():
        raise asyncio.CancelledError

    client.xmppclient.connected_event.wait = cancelled_wait

    with pytest.raises(asyncio.CancelledError):
        await coordinator.connect()

    assert not coordinator.is_connecting
