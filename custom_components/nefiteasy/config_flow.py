"""Config flow for Nefit Easy Bosch Thermostat integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .const import (  # pylint:disable=unused-import
    CONF_ACCESSKEY,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSORS,
    CONF_SERIAL,
    CONF_SWITCHES,
    CONF_TEMP_STEP,
    DOMAIN,
    SENSOR_TYPES,
    SWITCH_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class NefitEasyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nefit Easy Bosch Thermostat."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Init nefity easy config flow."""
        self._serial = None
        self._accesskey = None
        self._password = None

    async def async_step_user(self, user_input=None):
        """Step when user initializes an integration."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SERIAL])
            self._abort_if_unique_id_configured()

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

    async def async_step_options(self, user_input=None):
        """Step to set options."""
        errors = {}
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

    async def async_step_import(self, import_config=None):
        """Handle the initial step."""
        await self.async_set_unique_id(import_config[CONF_SERIAL])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"{import_config[CONF_SERIAL]}", data=import_config
        )
