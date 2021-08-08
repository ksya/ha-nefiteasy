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
from .const import DOMAIN, SELECT_TYPES
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

    for key in SELECT_TYPES:
        typeconf = SELECT_TYPES[key]
        entities.append(NefitSelect(client, data, key, typeconf))

    async_add_entities(entities, True)


class NefitSelect(NefitEntity, SelectEntity):
    """Representation of a NefitSwitch entity."""

    def __init__(
        self,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
        key: str,
        typeconf: Any,
    ):
        """Init Nefit Switch."""
        super().__init__(client, data, key, typeconf)

        self._attr_options = list(self._typeconf["options"].values())

    @property
    def current_option(self) -> str | None:
        """Return the state of the entity."""
        option = self.coordinator.data.get(self._key)
        if option is not None:
            return str(self._typeconf["options"][option])
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        option_dict = self._typeconf["options"]
        value = list(option_dict.keys())[list(option_dict.values()).index(option)]
        self._client.nefit.put_value(self.get_endpoint(), value)
