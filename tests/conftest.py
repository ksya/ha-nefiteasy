"""Test configuration of the nefiteasy integration."""
import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.custom_components.nefiteasy.const import SWITCHES
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry, load_fixture


@pytest.fixture
async def nefit_switch_wrapper(nefit_config, hass):
    """Setups a nefiteasy switch wrapper with mocked device."""
    config_entry = nefit_config

    entity_registry = er.async_get(hass)

    for description in SWITCHES:
        if (
            description.entity_registry_enabled_default is False
            and description.key != "home_entrance_detection"
        ):
            entity_registry.async_get_or_create(
                domain="switch",
                platform="nefiteasy",
                unique_id=f"123456789_{description.key}",
                config_entry=config_entry,
                original_name=description.name,
            )


@pytest.fixture
async def nefit_sensor_wrapper(nefit_config, hass):
    """Setups a nefiteasy sensor wrapper with mocked device."""
    config_entry = nefit_config

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        domain="sensor",
        platform="nefiteasy",
        unique_id="123456789_hot_water_operation",
        config_entry=config_entry,
        original_name="Hot water operation",
    )
    entity_registry.async_get_or_create(
        domain="sensor",
        platform="nefiteasy",
        unique_id="123456789_inhouse_temperature",
        config_entry=config_entry,
        original_name="Inhouse temperature",
    )


@pytest.fixture
async def nefit_select_wrapper(nefit_config, hass):
    """Setups a nefiteasy select wrapper with mocked device."""
    config_entry = nefit_config

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        domain="select",
        platform="nefiteasy",
        unique_id="123456789_active_program",
        config_entry=config_entry,
        original_name="Active program",
    )


@pytest.fixture
async def nefit_number_wrapper(nefit_config, hass):
    """Setups a nefiteasy number wrapper with mocked device."""
    config_entry = nefit_config

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        domain="number",
        platform="nefiteasy",
        unique_id="123456789_shower_timer_duration",
        config_entry=config_entry,
        original_name="Shower timer duration",
    )


@pytest.fixture
@patch("homeassistant.components.nefiteasy.NefitCore")
async def nefit_wrapper(nefit_mock, hass, nefit_config):
    """Setups a nefiteasy wrapper with mocked device."""
    config_entry = nefit_config

    client = ClientMock(nefit_mock)
    nefit_mock.return_value = client

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    return client


@pytest.fixture
@patch("homeassistant.components.nefiteasy.NefitCore")
async def nefit_wrapper_precense(nefit_mock, hass, nefit_config):
    """Setups a nefiteasy wrapper with mocked device."""
    config_entry = nefit_config

    client = ClientMock(nefit_mock)
    nefit_mock.return_value = client

    client.data["/ecus/rrc/homeentrancedetection/userprofile1/active"] = {
        "id": "/ecus/rrc/homeentrancedetection/userprofile1/active",
        "type": "stringValue",
        "recordable": 0,
        "writeable": 1,
        "value": "on",
    }
    client.data["/ecus/rrc/homeentrancedetection/userprofile1/name"] = {
        "id": "/ecus/rrc/homeentrancedetection/userprofile1/name",
        "type": "stringValue",
        "recordable": 0,
        "writeable": 1,
        "value": "my_device",
    }
    client.data["/ecus/rrc/homeentrancedetection/userprofile1/detected"] = {
        "id": "/ecus/rrc/homeentrancedetection/userprofile1/detected",
        "type": "stringValue",
        "recordable": 0,
        "writeable": 1,
        "value": "on",
    }

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    return client


@pytest.fixture
async def nefit_config(hass):
    """Setups nefit mock config entry."""
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

    return config_entry


class ClientMock:
    """A mock of the NefitCore."""

    def __init__(self, mock) -> None:
        """Create a mocked client."""
        self.xmppclient = MagicMock()

        self.xmppclient.connected_event = asyncio.Event()
        self.xmppclient.message_event = asyncio.Event()

        self.serial_number = None
        self.callback = None

        self.mock = mock

        self.data = json.loads(load_fixture("nefiteasy/nefit_data.json"))

    def get(self, path):
        """Get data."""
        if path in self.data:
            loop = asyncio.get_event_loop()
            coroutine = self.callback(self.data[path])
            loop.create_task(coroutine)

        self.xmppclient.message_event.set()

    async def connect(self):
        """Connect."""
        self.xmppclient.connected_event.set()

        self.serial_number = self.mock.call_args_list[0][1]["serial_number"]
        self.callback = self.mock.call_args_list[0][1]["message_callback"]

        return

    async def force_update_data(self, path):
        """Force update of an endpoint."""
        if path in self.data:
            await self.callback(self.data[path])

    async def disconnect(self):
        """Disconnect."""
        return

    def set_usermode(self, mode):
        """Set user mode."""
        self.data["/ecus/rrc/uiStatus"]["value"]["UMD"] = mode

    def set_temperature(self, temperature):
        """Set temperature."""
        self.data["/ecus/rrc/uiStatus"]["value"]["TSP"] = temperature

    def put_value(self, path, value):
        """Set a value."""
        if path in self.data:
            self.data[path]["value"] = value
