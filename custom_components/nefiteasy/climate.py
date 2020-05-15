"""
Support for Bosch home thermostats.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xxxxxx/
"""

import asyncio
import concurrent
import logging

try:
    from homeassistant.components.climate import ClimateEntity
except ImportError:
    from homeassistant.components.climate import ClimateDevice as ClimateEntity
from homeassistant.components.climate.const import (SUPPORT_TARGET_TEMPERATURE, SUPPORT_PRESET_MODE,
    CURRENT_HVAC_IDLE, CURRENT_HVAC_HEAT,
    HVAC_MODE_HEAT)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.const import STATE_UNKNOWN, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, CONF_NAME, CONF_MIN_TEMP, CONF_MAX_TEMP, CONF_TEMP_STEP, DISPATCHER_ON_DEVICE_UPDATE, STATE_CONNECTION_VERIFIED

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE)

# supported operating modes (preset mode)
OPERATION_MANUAL = "Manual"
OPERATION_CLOCK = "Clock"

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):

    entities = []
    for device in hass.data[DOMAIN]["devices"]:
        entities.append(NefitThermostat(device))

    async_add_entities(entities, update_before_add=True)
    _LOGGER.debug("climate: async_setup_platform done")


class NefitThermostat(ClimateEntity):
    """Representation of a NefitThermostat device."""

    def __init__(self, device):
        """Initialize the thermostat."""
        self._client = device['client']
        self._config = device['config']
        self._key = 'uistatus'
        self._url = '/ecus/rrc/uiStatus'
        self._unique_id = "%s_%s" % (self._client.nefit.serial_number, 'climate')

        self._client.events[self._key] = asyncio.Event()
        self._client.keys[self._url] = self._key

        self._unit_of_measurement = TEMP_CELSIUS
        self._data = {}
        self._hvac_modes = [HVAC_MODE_HEAT]

        self._remove_callbacks: List[Callable[[], None]] = []

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        kwargs = {
            "key": self._key,
        }
        self._remove_callbacks.append(
            async_dispatcher_connect(
                self.hass, DISPATCHER_ON_DEVICE_UPDATE.format(**kwargs), self.async_schedule_update_ha_state
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks."""
        for remove_callback in self._remove_callbacks:
            remove_callback()
        self._remove_callbacks = []

    @property
    def supported_features(self):
        """Return the list of supported features.
        """
        return SUPPORT_FLAGS

    @property
    def target_temperature_step(self):
        return self._config.get(CONF_TEMP_STEP)

    async def async_update(self):
        """Get latest data."""
        if self._client.connected_state == STATE_CONNECTION_VERIFIED:
            _LOGGER.debug("async_update called for climate device")
            event = self._client.events[self._key]
            event.clear() #clear old event
            self._client.nefit.get(self._url)
            try:
                await asyncio.wait_for(event.wait(), timeout=9)
            except concurrent.futures._base.TimeoutError:
                _LOGGER.debug("Did not get an update in time for %s %s.", self._client.serial, 'climate')
                event.clear() #clear event

    @property
    def name(self):
        """Return the name of the ClimateEntity.
        """
        return self._config.get(CONF_NAME)

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id
        
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
            'last_update': self._client.data.get('last_update'),
            'boiler_indicator': self._client.data.get('boiler_indicator')
        }

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._config.get(CONF_MIN_TEMP)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._config.get(CONF_MAX_TEMP)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target operation mode."""
        _LOGGER.debug("set_preset_mode called mode={}.".format(preset_mode))
        if preset_mode == OPERATION_CLOCK:
            new_mode = "clock"
        else:
            new_mode = "manual"

        self._client.nefit.set_usermode(new_mode)
        await asyncio.wait_for(self._client.nefit.xmppclient.message_event.wait(), timeout=9)
        self._client.nefit.xmppclient.message_event.clear()
        self._client.data['user_mode'] = new_mode

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("set_temperature called (temperature={}).".format(temperature))
        self._client.nefit.set_temperature(temperature)
        await asyncio.wait_for(self._client.nefit.xmppclient.message_event.wait(), timeout=9)
        self._client.nefit.xmppclient.message_event.clear()        
