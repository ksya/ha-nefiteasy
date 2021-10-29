"""Support for Bosch home thermostats."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NefitEasy
from .const import CONF_NAME, CONF_SERIAL, DOMAIN
from .models import NefitEntityDescription

_LOGGER = logging.getLogger(__name__)


class NefitEntity(CoordinatorEntity):
    """Representation of a Nefit entity."""

    entity_description: NefitEntityDescription

    def __init__(
        self,
        entity_description: NefitEntityDescription,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(client)

        self.entity_description = entity_description

        self._client = client
        self._config = data
        self._attr_unique_id = (
            f"{client.nefit.serial_number}_{self.entity_description.key}"
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._config[CONF_SERIAL])},
            "name": self._config[CONF_NAME],
            "manufacturer": "Bosch",
        }

    async def async_added_to_hass(self) -> None:
        """Add required data to coordinator."""
        await self._client.add_key(self.entity_description)
        await super().async_added_to_hass()

    def get_endpoint(self) -> Any:
        """Get end point."""
        return self.entity_description.url
