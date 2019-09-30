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

from . import DOMAIN, NefitDevice

_LOGGER = logging.getLogger(__name__)

name = 'name'
key = 'key'
url = 'url'

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    client = hass.data[DOMAIN]["client"]

    async_add_entities([
        NefitHotWater(client, {name: "Nefit Hot Water", key: 'hot_water'}),
        NefitSwitch(client, {name: "Nefit Holiday Mode", key: 'holiday_mode', url: '/heatingCircuits/hc1/holidayMode/activated'}),
        NefitSwitch(client, {name: "Nefit Fireplace Mode", key: 'fireplace_mode', url: '/ecus/rrc/userprogram/fireplacefunction'}),
        NefitSwitch(client, {name: "Nefit Today as Sunday", key: 'today_as_sunday', url: '/ecus/rrc/dayassunday/day10/active'}),
        NefitSwitch(client, {name: "Nefit Tomorrow as Sunday", key: 'tomorrow_as_sunday', url: '/ecus/rrc/dayassunday/day11/active'}),
        NefitSwitch(client, {name: "Nefit Preheating", key: 'preheating', url: '/ecus/rrc/userprogram/preheating'}),
        ], True)
    _LOGGER.debug("switch: async_setup_platform done")


class NefitSwitch(NefitDevice, SwitchDevice):
    """Representation of a NefitSwitch device."""

    @property
    def is_on(self):
        """Get whether the switch is in on state."""
        return self._client.data[self._key] == 'on'

    @property
    def assumed_state(self) -> bool:
        """Return true if we do optimistic updates."""
        return False

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self._client.nefit.put_value(self.get_endpoint(), "on")

        _LOGGER.debug("Switch Nefit %s ON, endpoint=%s.", self._key, self.get_endpoint())

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self._client.nefit.put_value(self.get_endpoint(), "off")

        _LOGGER.debug("Switch Nefit %s OFF, endpoint=%s.", self._key, self.get_endpoint())


class NefitHotWater(NefitSwitch):

    def __init__(self, client, device):
        """Initialize the switch."""
        self._client = client
        self._device = device
        self._key = device['key']
        client.events[self._key] = asyncio.Event()
        client.keys['/dhwCircuits/dhwA/dhwOperationClockMode'] = self._key
        client.keys['/dhwCircuits/dhwA/dhwOperationManualMode'] = self._key

        self._remove_callbacks: List[Callable[[], None]] = []
        
    def get_endpoint(self):
        endpoint = 'dhwOperationClockMode' if self._client.data.get('user_mode') == 'clock' else 'dhwOperationManualMode'
        return '/dhwCircuits/dhwA/' + endpoint