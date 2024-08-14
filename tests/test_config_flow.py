"""Tests of the config flow of the nefiteasy integration."""
import asyncio
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.nefiteasy import DOMAIN

from .conftest import ClientMock


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup(mock_class, hass: HomeAssistant):
    """Test we can setup the component."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"serial": "123456789", "accesskey": "myAccessKey", "password": "mypassword"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "options"
    assert result["errors"] == {}

    with patch("custom_components.nefiteasy.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"min_temp": 12, "max_temp": 32, "temp_step": 0.2},
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "123456789"
    assert result["data"] == {
        "serial": "123456789",
        "accesskey": "myAccessKey",
        "password": "mypassword",
        "min_temp": 12,
        "max_temp": 32,
        "temp_step": 0.2,
        "name": "Nefit",
    }


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_invalid_credentials(mock_class, hass: HomeAssistant):
    """Test we can setup network."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    async def connect():
        loop = asyncio.get_event_loop()
        coroutine = client.failed_auth_handler("auth_error")
        loop.create_task(coroutine)

    client.connect = connect

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "serial": "123456789",
            "accesskey": "myAccessKey",
            "password": "mypassword",
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_credentials"}


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_invalid_password(mock_class, hass: HomeAssistant):
    """Test we can setup network."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    async def set_msg_event():
        client.xmppclient.message_event.set()

    def get(path):
        loop = asyncio.get_event_loop()
        coroutine = client.failed_auth_handler("auth_error_password")
        loop.create_task(coroutine)

        coroutine2 = set_msg_event()
        loop.create_task(coroutine2)

    client.get = get

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "serial": "123456789",
            "accesskey": "myAccessKey",
            "password": "mypassword",
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_password"}


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_connect_timeout(mock_class, hass: HomeAssistant):
    """Test we can setup network."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    async def wait():
        raise asyncio.TimeoutError

    client.xmppclient.connected_event.wait = wait

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "serial": "123456789",
            "accesskey": "myAccessKey",
            "password": "mypassword",
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_message_timeout(mock_class, hass: HomeAssistant):
    """Test we can setup network."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    async def wait():
        raise asyncio.TimeoutError

    client.xmppclient.message_event.wait = wait

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "serial": "123456789",
            "accesskey": "myAccessKey",
            "password": "mypassword",
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_communicate"}
