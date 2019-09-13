"""
Support for Bosch home thermostats.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xxxxxx/
"""

import asyncio
import logging
import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (SUPPORT_TARGET_TEMPERATURE, SUPPORT_PRESET_MODE,
    CURRENT_HVAC_IDLE, CURRENT_HVAC_HEAT,
    HVAC_MODE_HEAT)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.const import STATE_UNKNOWN, EVENT_HOMEASSISTANT_STOP

from . import DOMAIN, CONF_NAME, CONF_MIN_TEMP, CONF_MAX_TEMP

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE)

# supported operating modes (preset mode)
OPERATION_MANUAL = "Manual"
OPERATION_CLOCK = "Clock"

async def async_setup_platform(hass, hass_config, async_add_entities, discovery_info=None):
    client = hass.data[DOMAIN]["client"]
    config = hass.data[DOMAIN]["config"]

    async_add_entities([NefitThermostat(client, config)], update_before_add=False)
    _LOGGER.debug("climate: async_setup_platform done")


class NefitThermostat(ClimateDevice):
    """Representation of a NefitThermostat device."""

    def __init__(self, client, config):
        """Initialize the thermostat."""
        self._client = client
        self.config = config

        self.watch_events = ['/ecus/rrc/uiStatus']

        self._unit_of_measurement = TEMP_CELSIUS
        self._data = {}
        self._hvac_modes = [HVAC_MODE_HEAT]


    @property
    def supported_features(self):
        """Return the list of supported features.
        """
        return SUPPORT_FLAGS

    @property
    def target_temperature_step(self):
        return 0.5

            
    async def async_update(self):
        """Get latest data
        """
        _LOGGER.debug("climate: async_update called")
        tasks = []
        for url in self.watch_events:
            event = self._client.events[url]
            event.clear()
            self._client.nefit.get(url)
            tasks.append(asyncio.wait_for(event.wait(), timeout=10))
        
        await asyncio.gather(*tasks)
    
        _LOGGER.debug("climate: async_update finished")

    @property
    def name(self):
        """Return the name of the ClimateDevice.
        """
        return self.config.get(CONF_NAME)

    @property
    def temperature_unit(self):
        """Return the unit of measurement.
        """
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the current temperature.
        """
        return self._client.data.get('inhouse_temperature')

    @property
    def target_temperature(self):
        return self._client.data.get('temp_setpoint')

    @property
    def hvac_modes (self):
        """List of available modes."""
        return self._hvac_modes

    @property
    def hvac_mode(self):
        return HVAC_MODE_HEAT
    
    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        if self._client.data.get('boiler_indicator') == 'CH': #HW (hot water) is not for climate
            return CURRENT_HVAC_HEAT
        
        return CURRENT_HVAC_IDLE

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return [
            OPERATION_MANUAL,
            OPERATION_CLOCK
        ]


    @property
    def preset_mode(self):
        """Return the current preset mode."""
        if self._client.data.get('user_mode') == 'manual':
            return OPERATION_MANUAL
        elif self._client.data.get('user_mode') == 'clock':
            return OPERATION_CLOCK
        else:
            return OPERATION_MANUAL

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        return {
            'last_update': self._client.data.get('last_update')
        }

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self.config.get(CONF_MIN_TEMP)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self.config.get(CONF_MAX_TEMP)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target operation mode."""
        _LOGGER.debug("set_preset_mode called mode={}.".format(preset_mode))
        if preset_mode == OPERATION_CLOCK:
            new_mode = "clock"
        else:
            new_mode = "manual"

        self._client.nefit.set_usermode(new_mode)
        await asyncio.wait_for(self._client.nefit.xmppclient.message_event.wait(), timeout=10.0)
        self._client.nefit.xmppclient.message_event.clear()
        self._client.data['user_mode'] = new_mode

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("set_temperature called (temperature={}).".format(temperature))
        self._client.nefit.set_temperature(temperature)
        await asyncio.wait_for(self._client.nefit.xmppclient.message_event.wait(), timeout=10.0)
        self._client.nefit.xmppclient.message_event.clear()        
