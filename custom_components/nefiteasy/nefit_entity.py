"""Support for Bosch home thermostats."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NefitEasy
from .const import CONF_NAME, CONF_SERIAL, DOMAIN, url

_LOGGER = logging.getLogger(__name__)


class NefitEntity(CoordinatorEntity):
    """Representation of a Nefit entity."""

    def __init__(
        self,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
        key: str,
        typeconf: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(client)

        self._client = client

        self._config = data
        self._typeconf = typeconf
        self._key = key
        self._attr_unique_id = f"{client.nefit.serial_number}_{self._key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._config[CONF_SERIAL])},
            "name": self._config[CONF_NAME],
            "manufacturer": "Bosch",
        }

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return f'{self._config[CONF_NAME]} {self._typeconf["name"]}'

    @property
    def icon(self) -> str | None:
        """Return possible sensor specific icon."""
        if "icon" in self._typeconf:
            return str(self._typeconf["icon"])
        return None

    async def async_added_to_hass(self) -> None:
        """Add required data to coordinator."""
        await self._client.add_key(self._key, self._typeconf)
        await super().async_added_to_hass()

    def get_endpoint(self) -> Any:
        """Get end point."""
        return self._typeconf[url]
