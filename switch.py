"""
Support for Bosch home thermostats.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xxxxxx/
"""

import asyncio
import logging
import voluptuous as vol

from homeassistant.components.switch import SwitchDevice
from homeassistant.const import STATE_OFF, STATE_ON

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    client = hass.data[DOMAIN]["client"]

    async_add_entities([
        NefitHotWater(client, "Nefit Hot Water", 'hot_water'),
        NefitSwitch(client, "Nefit Holiday Mode", 'holiday_mode', '/heatingCircuits/hc1/holidayMode/status'),
        NefitSwitch(client, "Nefit Fireplace Mode", 'fireplace_mode', '/ecus/rrc/userprogram/fireplacefunction'),
        NefitSwitch(client, "Nefit Today as Sunday", 'today_as_sunday', '/ecus/rrc/dayassunday/day10/active'),
        NefitSwitch(client, "Nefit Tomorrow as Sunday", 'tomorrow_as_sunday', '/ecus/rrc/dayassunday/day11/active'),
        NefitSwitch(client, "Nefit Preheating", 'preheating', '/ecus/rrc/userprogram/preheating'),
        ], True)
    _LOGGER.debug("switch: async_setup_platform done")


class NefitSwitch(SwitchDevice):
    """Representation of a NefitSwitch device."""

    def __init__(self, client, name, id, url):
        """Initialize the switch."""
        self._client = client

        self._url = url
        self._id = id
        self._name = name
        self._optimistic = False
        client.events[self._url] = asyncio.Event()
        client.ids[self._url] = self._id
        pass

    @property
    def name(self):
        """Return the name of the switch. """
        return self._name

    @property
    def is_on(self):
        """Get whether the switch is in on state."""
        return self._client.data[self._id] == 'on'

    def get_endpoint(self):
        return self._url

    @property
    def assumed_state(self) -> bool:
        """Return true if we do optimistic updates."""
        return self._optimistic

    @property
    def should_poll(self) -> bool:
        """Return False as this device should never be polled."""
        return True

    async def async_update(self):
        """Get latest data."""
        _LOGGER.debug("switch: async_update called for switch {}".format(self.name))
        tasks = []
        event = self._client.events[self._url]
        event.clear()
        self._client.nefit.get(self.get_endpoint())
        tasks.append(asyncio.wait_for(event.wait(), timeout=10))
        
        await asyncio.gather(*tasks)
    
        _LOGGER.debug("switch: async_update finished for switch {}".format(self.name))

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self._client.nefit.put_value(self.get_endpoint(), "on")
        # await asyncio.wait_for(self._client.events[self._id].wait(), timeout=10.0)
        # self._client.nefit.xmppclient.message_event.clear()

        _LOGGER.debug("Switch Nefit {} ON, endpoint={}.".format(self._id, self.get_endpoint()))

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self._client.nefit.put_value(self.get_endpoint(), "off")
        # await asyncio.wait_for(self._client.events[self._id].wait(), timeout=10.0)
        # self._client.nefit.xmppclient.message_event.clear()

        _LOGGER.debug("Switch Nefit {} OFF, endpoint={}.".format(self._id, self.get_endpoint()))


class NefitHotWater(NefitSwitch):

    def __init__(self, client, name, id):
        """Initialize the switch."""
        self._client = client

        self._url = None
        self._id = id
        self._name = name
        self._optimistic = False

        client.events[self._id] = asyncio.Event()
        
    async def async_update(self):
        """Get latest data."""
        _LOGGER.debug("switch: async_update called for switch {}".format(self.name))
        tasks = []
        event = self._client.events[self._id]
        event.clear()
        self._client.nefit.get(self.get_endpoint())
        tasks.append(asyncio.wait_for(event.wait(), timeout=10))
        
        await asyncio.gather(*tasks)
    
        _LOGGER.debug("switch: async_update finished for switch {}".format(self.name))

    def get_endpoint(self):
        endpoint = 'dhwOperationClockMode' if self._client.data.get('user_mode') == 'clock' else 'dhwOperationManualMode'
        return '/dhwCircuits/dhwA/' + endpoint