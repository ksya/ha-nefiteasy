"""Config flow for Nefit Easy Bosch Thermostat integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from aionefit import NefitCore
from homeassistant import config_entries, core, exceptions
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (  # pylint:disable=unused-import
    AUTH_ERROR_CREDENTIALS,
    AUTH_ERROR_PASSWORD,
    CONF_ACCESSKEY,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SERIAL,
    CONF_TEMP_STEP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class NefitConnection:
    """Test the connection to NefitEasy and check read to verify description of messages."""

    def __init__(self, serial_number: str, access_key: str, password: str) -> None:
        """Initialize."""
        self.nefit = NefitCore(
            serial_number=serial_number,
            access_key=access_key,
            password=password,
        )

        self.nefit.failed_auth_handler = self.failed_auth_handler
        self.nefit.no_content_callback = self.no_content_callback
        self.nefit.session_end_callback = self.session_end_callback

        self.auth_failure = None

    async def failed_auth_handler(self, event: str) -> None:
        """Report failed auth."""
        self.nefit.xmppclient.connected_event.set()

        if event == "auth_error_password":
            self.auth_failure = AUTH_ERROR_PASSWORD
            _LOGGER.debug("Invalid password for connecting to Bosch cloud.")
        else:
            self.auth_failure = AUTH_ERROR_CREDENTIALS
            _LOGGER.debug(
                "Invalid credentials (serial or accesskey) for connecting to Bosch cloud."
            )

    async def session_end_callback(self) -> None:
        """Session end."""

    async def no_content_callback(self, data: Any) -> None:
        """No content."""

    async def validate_connect(self) -> None:
        """Test if we can connect and communicate with the device."""

        await self.nefit.connect()
        try:
            await asyncio.wait_for(
                self.nefit.xmppclient.connected_event.wait(), timeout=10.0
            )
        except asyncio.TimeoutError as ex:
            self.nefit.xmppclient.cancel_connection_attempt()
            raise CannotConnect from ex

        if self.auth_failure == AUTH_ERROR_CREDENTIALS:
            raise InvalidCredentials

        self.nefit.get("/gateway/brandID")
        try:
            await asyncio.wait_for(
                self.nefit.xmppclient.message_event.wait(), timeout=10.0
            )
        except asyncio.TimeoutError as ex:
            self.nefit.xmppclient.cancel_connection_attempt()
            raise CannotCommunicate from ex

        self.nefit.xmppclient.message_event.clear()

        await self.nefit.disconnect()

        if self.auth_failure == AUTH_ERROR_PASSWORD:
            raise InvalidPassword


async def _validate_nefiteasy_connection(
    hass: core.HomeAssistant, data: dict[str, Any]
) -> None:
    """Validate the user input allows us to connect."""
    conn = NefitConnection(
        data.get(CONF_SERIAL), data[CONF_ACCESSKEY], data[CONF_PASSWORD]
    )

    await conn.validate_connect()


class NefitEasyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nefit Easy Bosch Thermostat."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Init nefity easy config flow."""
        self._serial = None
        self._accesskey = None
        self._password = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step when user initializes an integration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SERIAL])
            self._abort_if_unique_id_configured()

            try:
                await _validate_nefiteasy_connection(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except CannotCommunicate:
                errors["base"] = "cannot_communicate"
            except InvalidCredentials:
                errors["base"] = "invalid_credentials"
            except InvalidPassword:
                errors["base"] = "invalid_password"

            if not errors:
                self._serial = user_input[CONF_SERIAL]
                self._accesskey = user_input[CONF_ACCESSKEY]
                self._password = user_input[CONF_PASSWORD]

                return await self.async_step_options()

        schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL): cv.string,
                vol.Required(CONF_ACCESSKEY): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step to set options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_SERIAL: self._serial,
                CONF_ACCESSKEY: self._accesskey,
                CONF_PASSWORD: self._password,
                CONF_MIN_TEMP: user_input[CONF_MIN_TEMP],
                CONF_MAX_TEMP: user_input[CONF_MAX_TEMP],
                CONF_TEMP_STEP: user_input[CONF_TEMP_STEP],
                CONF_NAME: "Nefit",
            }

            return self.async_create_entry(title=f"{self._serial}", data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_MIN_TEMP, default=10): cv.positive_int,
                vol.Required(CONF_MAX_TEMP, default=28): cv.positive_int,
                vol.Required(CONF_TEMP_STEP, default=0.5): cv.small_float,
            }
        )

        return self.async_show_form(
            step_id="options", data_schema=schema, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class CannotCommunicate(exceptions.HomeAssistantError):
    """Error to indicate we cannot communicate."""


class InvalidCredentials(exceptions.HomeAssistantError):
    """Error to indicate we cannot verify credentials."""


class InvalidPassword(exceptions.HomeAssistantError):
    """Error to indicate we cannot verify password."""
