"""
Support for Bosch home thermostats.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xxxxxx/
"""

import asyncio
import logging
import voluptuous as vol

from homeassistant.const import (TEMP_CELSIUS, PRESSURE_BAR, ATTR_TEMPERATURE, ENERGY_KILO_WATT_HOUR, 
    DEVICE_CLASS_TEMPERATURE)
#from homeassistant.core import callback

from . import DOMAIN, NefitDevice

_LOGGER = logging.getLogger(__name__)

name = 'name'
key = 'key'
url = 'url'
unit = 'unit'
device_class = 'device_class'

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    client = hass.data[DOMAIN]["client"]

    async_add_entities([
        NefitYearTotal(client, {name: "Nefit Year Total", key: 'year_total',  url: '/ecus/rrc/recordings/yearTotal', unit: 'm3'}),
        NefitStatus(client, {name: "Nefit Status", key: 'status',  url: '/system/appliance/displaycode'}),
        NefitSensor(client, {name: "Nefit Supply Temperature", key: 'supply_temperature', url: '/heatingCircuits/hc1/actualSupplyTemperature', unit: TEMP_CELSIUS, device_class: 'temperature'}),
        NefitSensor(client, {name: "Nefit CV Pressure", key: 'system_pressure',  url: '/system/appliance/systemPressure', unit: PRESSURE_BAR, device_class: 'pressure'}),
        NefitSensor(client, {name: "Nefit Outdoor Temperature", key: 'outdoor_temperature',  url: '/system/sensors/temperatures/outdoor_t1', unit: TEMP_CELSIUS, device_class: 'temperature'}),
        NefitSensor(client, {name: "Nefit Active Program", key: 'active_program',  url: '/ecus/rrc/userprogram/activeprogram'}),
        ], True)
    _LOGGER.debug("sensor: async_setup_platform done")


class NefitSensor(NefitDevice):
    """Representation of a NefitSensor device."""

    @property
    def state(self):
        """Return the state/value of the sensor."""
        return self._client.data[self._key]

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        if 'device_class' in self._device:
            return self._device['device_class']
        else:
            return None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of the sensor."""
        if 'unit' in self._device:
            return self._device['unit']
        else:
            return None



class NefitYearTotal(NefitSensor):
    """Representation of the total year consumption."""

    @property
    def state(self):
        """Return the state/value of the sensor."""
        return "{0:.1f}".format(self._client.data[self._key] * 0.12307692) #convert kWh to m3, for LPG, multiply with 0.040742416


class NefitStatus(NefitSensor):
    """Representation of the boiler status."""

    @property
    def state(self):
        """Return the state/value of the sensor."""
        return self.get_status(self._client.data[self._key])

    def get_status(self, code):
        display_codes = {
            '-H': 'central heating active',
            '=H': 'hot water active',
            '0C': 'system starting',
            '0L': 'system starting',
            '0U': 'system starting',
            '0E': 'system waiting',
            '0H': 'system standby',
            '0A': 'system waiting (boiler cannot transfer heat to central heating)',
            '0Y': 'system waiting (boiler cannot transfer heat to central heating)',
            '2E': 'boiler water pressure too low',
            'H07': 'boiler water pressure too low',
            '2F': 'sensors measured abnormal temperature',
            '2L': 'sensors measured abnormal temperature',
            '2P': 'sensors measured abnormal temperature',
            '2U': 'sensors measured abnormal temperature',
            '4F': 'sensors measured abnormal temperature',
            '4L': 'sensors measured abnormal temperature',
            '6A': 'burner doesn\'t ignite',
            '6C': 'burner doesn\'t ignite',
            'rE': 'system restarting'
        }
        if code in display_codes:
            return display_codes[code]
        else:
            return 'unknown code '+code