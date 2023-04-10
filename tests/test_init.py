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
