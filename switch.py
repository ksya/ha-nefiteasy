"""
Support for Bosch home thermostats.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xxxxxx/
"""

import asyncio
import logging

from homeassistant.components.switch import SwitchDevice
from homeassistant.const import STATE_OFF, STATE_ON

from .const import DOMAIN, CONF_SWITCHES, SWITCH_TYPES
from .nefit_device import NefitDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    client = hass.data[DOMAIN]["client"]

    devices = []
    for key in hass.data[DOMAIN]["config"][CONF_SWITCHES]:
        dev = SWITCH_TYPES[key]
        if key == 'hot_water':
            devices.append(NefitHotWater(client, key, dev))
        elif key == 'home_entrance_detection':
            await setup_home_entrance_detection(devices, client, key, dev)
        else:
            devices.append(NefitSwitch(client, key, dev))

    async_add_entities(devices, True)

    _LOGGER.debug("switch: async_setup_platform done")


async def setup_home_entrance_detection(devices, client, basekey, basedev):
    for i in range(0, 10):
        userprofile_id = 'userprofile{}'.format(i)
        endpoint = '/ecus/rrc/homeentrancedetection/{}/'.format(userprofile_id)
        is_active = await client.get_value(userprofile_id, endpoint + 'active')
        _LOGGER.debug("hed switch: is_active: " + str(is_active))
        if is_active == 'on':
            name = await client.get_value(userprofile_id, endpoint + 'name')
            dev = {}
            dev['name'] = basedev['name'].format(name)
            dev['url'] = endpoint + 'detected'
            dev['icon'] = basedev['icon']
            devices.append(NefitSwitch(client, '{}_{}'.format(basekey, userprofile_id), dev))


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

    def __init__(self, client, key, device):
        """Initialize the switch."""
        super().__init__(client, key, device)

        client.keys['/dhwCircuits/dhwA/dhwOperationClockMode'] = self._key
        client.keys['/dhwCircuits/dhwA/dhwOperationManualMode'] = self._key
        
    def get_endpoint(self):
        endpoint = 'dhwOperationClockMode' if self._client.data.get('user_mode') == 'clock' else 'dhwOperationManualMode'
        return '/dhwCircuits/dhwA/' + endpoint