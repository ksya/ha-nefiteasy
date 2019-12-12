"""Config flow to configure the Nefit Easy integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from . import (
    CONF_SERIAL,
    CONF_ACCESSKEY,
    CONF_PASSWORD,
    CONF_NAME,
    DOMAIN
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ID

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class NefitEasyFlowHandler(ConfigFlow):
    """Handle a Nefit Easy config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="connect",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SERIAL): str,
                    vol.Required(CONF_ACCESSKEY): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        errors = {}

      
        entries = self._async_current_entries()
        for entry in entries:
            if entry.data[CONF_ID] == unique_id:
                return self.async_abort(reason="address_already_set_up")

        return self.async_create_entry(
            title=unique_id,
            data={
                CONF_ID: unique_id,
                CONF_SERIAL: user_input[CONF_SERIAL],
                CONF_ACCESSKEY: user_input[CONF_ACCESSKEY],
                CONF_PASSWORD: user_input.get(CONF_PASSWORD),
            },
        )
