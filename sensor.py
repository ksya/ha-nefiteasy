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
from homeassistant.helpers.entity import Entity
#from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    client = hass.data[DOMAIN]["client"]

    async_add_entities([
        NefitSensor(client, "Nefit Supply Temperature", 'supply_temperature', '/heatingCircuits/hc1/actualSupplyTemperature', TEMP_CELSIUS, 'temperature'),
        NefitSensor(client, "Nefit CV Pressure", 'system_pressure', '/system/appliance/systemPressure', PRESSURE_BAR, 'pressure'),
        NefitYearTotal(client, "Nefit Year Total", 'year_total', '/ecus/rrc/recordings/yearTotal', 'm3', None),
        NefitStatus(client, "Nefit Status", 'status', '/system/appliance/displaycode', None, None),
        NefitSensor(client, "Nefit Outdoor Temperature", 'outdoor_temperature', '/system/sensors/temperatures/outdoor_t1', TEMP_CELSIUS, 'temperature'),
        #NefitSensor(client, "Nefit Current Switchpoint", 'current_switchpoint', '/dhwCircuits/dhwA/dhwCurrentSwitchpoint', None, None),
        #NefitSensor(client, "Nefit Next Switchpoint", 'next_switchpoint', '/dhwCircuits/dhwA/dhwNextSwitchpoint', None, None),
        #NefitSensor(client, "Nefit Next Switchpoint 2", 'next_switchpoint2', '/ecus/rrc/selflearning/nextSwitchpoint', None, None),
        NefitSensor(client, "Nefit Active Program", 'active_program', '/ecus/rrc/userprogram/activeprogram', None, None),
        ], True)
    _LOGGER.debug("sensor: async_setup_platform done")


class NefitSensor(Entity):
    """Representation of a NefitSensor device."""

    def __init__(self, client, name, id, url, unit, device_class):
        """Initialize the sensor."""
        self._client = client

        self._id = id
        self._url = url
        self._name = name
        self._device_class = device_class
        self._unit_of_measurement = unit
        client.events[self._url] = asyncio.Event()
        client.ids[self._url] = self._id
        pass
        
    async def async_update(self):
        """Get latest data."""
        _LOGGER.debug("sensor: async_update called for sensor {}".format(self.name))
        tasks = []
        event = self._client.events[self._url]
        event.clear()
        self._client.nefit.get(self._url)
        tasks.append(asyncio.wait_for(event.wait(), timeout=10))
        
        await asyncio.gather(*tasks)
    
        _LOGGER.debug("sensor: async_update finished for sensor {}".format(self.name))

    # async def async_added_to_hass(self):
    #     """Set up a listener when this entity is added to HA.
    #     Called when an entity has their entity_id and hass object assigned, before it is written to the state machine for the first time. Example uses: restore the state, subscribe to updates or set callback/dispatch function/listener.
    #     """
    #     async_dispatcher_connect(self.hass, DOMAIN, self._refresh)

    # @callback
    # def _refresh(self):
    #     self.async_schedule_update_ha_state(force_refresh=True)

    @property
    def name(self):
        """Return the name of the sensor. """
        return self._name

    @property
    def state(self):
        """Return the state/value of the sensor."""
        return self._client.data[self._id]

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of the sensor."""
        return self._unit_of_measurement

    @property
    def should_poll(self) -> bool:
        """Return False as this device should never be polled."""
        return True


class NefitYearTotal(NefitSensor):
    """Representation of the total year consumption."""

    def __init__(self, client, name, id, url, unit, device_class):
        """Initialize the sensor."""
        super().__init__(client, name, id, url, unit, device_class)

    @property
    def state(self):
        """Return the state/value of the sensor."""
        return "{0:.1f}".format(self._client.data[self._id] * 0.12307692) #convert kWh to m3, for LPG, multiply with 0.040742416


class NefitStatus(NefitSensor):
    """Representation of the total year consumption."""

    def __init__(self, client, name, id, url, unit, device_class):
        """Initialize the sensor."""
        super().__init__(client, name, id, url, unit, device_class)

    @property
    def state(self):
        """Return the state/value of the sensor."""
        return self.get_status(self._client.data[self._id])

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