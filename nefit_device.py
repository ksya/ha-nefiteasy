import asyncio
import concurrent
import logging

from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (DISPATCHER_ON_DEVICE_UPDATE)

_LOGGER = logging.getLogger(__name__)

class NefitDevice(Entity):
    """Representation of a Nefit device."""

    def __init__(self, client, key, device):
        """Initialize the sensor."""
        self._client = client
        self._device = device
        self._key = key
        self._url = device['url']
        client.events[key] = asyncio.Event()
        client.keys[self._url] = key
        if 'short' in device:
            client.uiStatusVars[key] = device['short']

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

    async def async_update(self):
        """Request latest data."""
        _LOGGER.debug("async_update called for %s", self._key)
        event = self._client.events[self._key]
        event.clear() #clear old event
        self._client.nefit.get(self.get_endpoint())
        try:
            await asyncio.wait_for(event.wait(), timeout=10)
        except concurrent.futures._base.TimeoutError:
            _LOGGER.debug("Did not get an update in time for %s.", self._key)
            event.clear() #clear event
        
    @property
    def name(self):
        """Return the name of the device. """
        return self._device['name']

    def get_endpoint(self):
        """Return the API endpoint."""
        return self._device['url']

    @property
    def should_poll(self) -> bool:
        """Enable polling if value does not exist in uiStatus"""
        if 'short' in self._device:
            return False
        else:
            return True

    @property
    def icon(self):
        """Return possible sensor specific icon."""
        if 'icon' in self._device:
            return self._device['icon']