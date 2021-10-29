"""Support for Bosch home thermostats."""
from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NefitEasy
from .const import DOMAIN, SELECTS
from .models import NefitSelectEntityDescription
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

    for description in SELECTS:
        entities.append(NefitSelect(description, client, data))

    async_add_entities(entities, True)


class NefitSelect(NefitEntity, SelectEntity):
    """Representation of a NefitSwitch entity."""

    entity_description: NefitSelectEntityDescription

    def __init__(
        self,
        entity_description: NefitSelectEntityDescription,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
    ) -> None:
        """Init Nefit Switch."""
        super().__init__(entity_description, client, data)

        if self.entity_description.options is not None:
            self._attr_options = list(self.entity_description.options.values())

    @property
    def current_option(self) -> str | None:
        """Return the state of the entity."""
        option = self.coordinator.data.get(self.entity_description.key)
        if option is not None and self.entity_description.options is not None:
            return str(self.entity_description.options[option])
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        option_dict = self.entity_description.options
        if option_dict is not None:
            value = list(option_dict.keys())[list(option_dict.values()).index(option)]
            self._client.nefit.put_value(self.get_endpoint(), value)
