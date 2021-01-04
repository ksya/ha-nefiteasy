"""Support for Bosch home thermostats."""

import asyncio
import logging
from typing import Callable, Dict, List

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (
    CONF_NAME,
    CONF_SERIAL,
    DISPATCHER_ON_DEVICE_UPDATE,
    DOMAIN,
    STATE_CONNECTION_VERIFIED,
)

_LOGGER = logging.getLogger(__name__)


class NefitEntity(Entity):
    """Representation of a Nefit entity."""

    def __init__(self, client, data, key, typeconf):
        """Initialize the sensor."""
        self._client = client
        self._config = data
        self._typeconf = typeconf
        self._key = key
        self._unique_id = f"{self._client.nefit.serial_number}_{self._key}"

        self._client.events[key] = asyncio.Event()
        self._client.data[key] = None

        if "url" in typeconf:
            self._url = typeconf["url"]
            self._client.keys[self._url] = key

        if "short" in typeconf:
            self._client.ui_status_vars[key] = typeconf["short"]

        self._remove_callbacks: List[Callable[[], None]] = []

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        kwargs = {
            "key": self._key,
        }
        self._remove_callbacks.append(
            async_dispatcher_connect(
                self.hass,
                DISPATCHER_ON_DEVICE_UPDATE.format(**kwargs),
                self.async_schedule_update_ha_state,
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks."""
        for remove_callback in self._remove_callbacks:
            remove_callback()
        self._remove_callbacks = []

        del self._client.events[self._key]
        if self._key in self._client.ui_status_vars:
            del self._client.ui_status_vars[self._key]

    async def async_update(self):
        """Request latest data."""
        _LOGGER.debug("async_update called for %s", self._key)
        event = self._client.events[self._key]
        event.clear()  # clear old event
        self._client.nefit.get(self.get_endpoint())
        try:
            await asyncio.wait_for(event.wait(), timeout=9)
        except asyncio.TimeoutError:
            _LOGGER.debug(
                "Did not get an update in time for %s %s.",
                self._client.serial,
                self._key,
            )
            event.clear()  # clear event

    @property
    def name(self):
        """Return the name of the device."""
        return f'{self._config[CONF_NAME]} {self._typeconf["name"]}'

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        """Return if entity should poll."""
        if self._client.connected_state == STATE_CONNECTION_VERIFIED:
            # Enable polling if value does not exist in uiStatus
            if "short" in self._typeconf:
                return False

            return True

        return False

    @property
    def icon(self):
        """Return possible sensor specific icon."""
        if "icon" in self._typeconf:
            return self._typeconf["icon"]

    def get_endpoint(self):
        """Return the API endpoint."""
        return self._url

    @property
    def device_info(self) -> Dict[str, any]:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._config[CONF_SERIAL])},
            "name": self._config[CONF_NAME],
            "manufacturer": "Bosch",
        }
