"""Support for Bosch home thermostats."""

import logging
from typing import Dict

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, CONF_SERIAL, DOMAIN, url

_LOGGER = logging.getLogger(__name__)


class NefitEntity(CoordinatorEntity):
    """Representation of a Nefit entity."""

    def __init__(self, client, data, key, typeconf):
        """Initialize the sensor."""
        super().__init__(client)

        self._config = data
        self._typeconf = typeconf
        self._key = key
        self._unique_id = f"{client.nefit.serial_number}_{self._key}"

    @property
    def name(self):
        """Return the name of the device."""
        return f'{self._config[CONF_NAME]} {self._typeconf["name"]}'

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def icon(self):
        """Return possible sensor specific icon."""
        if "icon" in self._typeconf:
            return self._typeconf["icon"]

    @property
    def device_info(self) -> Dict[str, any]:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._config[CONF_SERIAL])},
            "name": self._config[CONF_NAME],
            "manufacturer": "Bosch",
        }

    async def async_added_to_hass(self):
        """Add required data to coordinator."""
        await self.coordinator.add_key(self._key, self._typeconf)
        await super().async_added_to_hass()

    def get_endpoint(self):
        """Get end point."""
        return self._typeconf[url]
