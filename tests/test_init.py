"""Tests of the initialization of the nefiteasy integration."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture
from .conftest import ClientMock


@patch("homeassistant.components.nefiteasy.NefitCore")
async def test_setup_entry(mock_class, hass: HomeAssistant):
    """Validate that setup entry also configure the client."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    config_entry = MockConfigEntry(
        domain="nefiteasy",
        data={
            "serial": "123456789",
            "accesskey": "myAccessKey",
            "password": "myPass",
            "min_temp": 10,
            "max_temp": 28,
            "temp_step": 0.5,
            "name": "Nefit",
        },
    )

    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)

    await hass.async_block_till_done()

    assert config_entry.state == config_entries.ConfigEntryState.LOADED
