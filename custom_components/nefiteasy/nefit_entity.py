import asyncio
import concurrent
import logging

from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DISPATCHER_ON_DEVICE_UPDATE, CONF_NAME, STATE_CONNECTION_VERIFIED

_LOGGER = logging.getLogger(__name__)

class NefitEntity(Entity):
    """Representation of a Nefit entity."""

    def __init__(self, device, key, typeconf):
        """Initialize the sensor."""
        self._client = device['client']
        self._config = device['config']
        self._typeconf = typeconf
        self._key = key
        self._unique_id = "%s_%s" % (self._client.nefit.serial_number, self._key)

        self._client.events[key] = asyncio.Event()
        self._client.data[key] = None

        if 'url' in typeconf:
            self._url = typeconf['url']
            self._client.keys[self._url] = key

        if 'short' in typeconf:
            self._client.uiStatusVars[key] = typeconf['short']

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
        
        del self._client.events[self._key] 
        del self._client.uiStatusVars[key]

    async def async_update(self):
        """Request latest data."""
        _LOGGER.debug("async_update called for %s", self._key)
        event = self._client.events[self._key]
        event.clear() #clear old event
        self._client.nefit.get(self.get_endpoint())
        try:
            await asyncio.wait_for(event.wait(), timeout=9)
        except concurrent.futures._base.TimeoutError:
            _LOGGER.debug("Did not get an update in time for %s %s.", self._client.serial, self._key)
            event.clear() #clear event
        
    @property
    def name(self):
        """Return the name of the device. """
        return "%s %s" % (self._config[CONF_NAME], self._typeconf['name'])

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        if self._client.connected_state == STATE_CONNECTION_VERIFIED:
            """Enable polling if value does not exist in uiStatus"""
            if 'short' in self._typeconf:
                return False
            else:
                return True
        else:
            return False

    @property
    def icon(self):
        """Return possible sensor specific icon."""
        if 'icon' in self._typeconf:
            return self._typeconf['icon']
        
    def get_endpoint(self):
        """Return the API endpoint."""
        return self._url