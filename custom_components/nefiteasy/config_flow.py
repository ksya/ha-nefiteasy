"""Config flow for Nefit Easy Bosch Thermostat integration."""
import logging

from homeassistant import config_entries

from .const import CONF_SERIAL, DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)


class NefitEasyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nefit Easy Bosch Thermostat."""

    VERSION = 1
    # TODO pick one of the available connection classes in homeassistant/config_entries.py
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_import(self, import_config=None):
        """Handle the initial step."""
        await self.async_set_unique_id(import_config[CONF_SERIAL])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"{import_config[CONF_SERIAL]}", data=import_config
        )
