"""Support for Bosch home thermostats."""
from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NefitEasy
from .const import DOMAIN, NUMBERS
from .models import NefitNumberEntityDescription
from .nefit_entity import NefitEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Switch setup for nefit easy."""
    entities: list[NefitEntity] = []

    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    data = config_entry.data

    for description in NUMBERS:
        entities.append(NefitNumber(description, client, data))

    async_add_entities(entities, True)


class NefitNumber(NefitEntity, NumberEntity):
    """Representation of a NefitSwitch entity."""

    entity_description: NefitNumberEntityDescription

    def __init__(
        self,
        entity_description: NefitNumberEntityDescription,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
    ) -> None:
        """Init Nefit Switch."""
        super().__init__(entity_description, client, data)

        if entity_description.min_value is not None:
            self._attr_min_value = entity_description.min_value
        if entity_description.max_value is not None:
            self._attr_max_value = entity_description.max_value
        if entity_description.step is not None:
            self._attr_step = entity_description.step

    @property
    def value(self) -> float | None:
        """Return the entity value to represent the entity state."""
        return self.coordinator.data.get(self.entity_description.key)

    async def async_set_value(self, value: float) -> None:
        """Update the current value."""
        self._client.nefit.put_value(self.get_endpoint(), value)
