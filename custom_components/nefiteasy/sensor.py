"""Support for Bosch home thermostats."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SENSOR_TYPES
from .nefit_entity import NefitEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensor platform setup for nefit easy."""
    entities: list[NefitEntity] = []

    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    data = config_entry.data

    for key in SENSOR_TYPES:
        typeconf = SENSOR_TYPES[key]
        if key == "status":
            entities.append(NefitStatus(client, data, key, typeconf))
        elif key == "year_total":
            entities.append(NefitYearTotal(client, data, key, typeconf))
        else:
            entities.append(NefitSensor(client, data, key, typeconf))

    async_add_entities(entities, True)


class NefitSensor(NefitEntity):
    """Representation of a NefitSensor entity."""

    @property
    def state(self) -> Any:
        """Return the state/value of the sensor."""
        return self.coordinator.data.get(self._key)

    @property
    def device_class(self) -> str | None:
        """Return the device class of the sensor."""
        if "device_class" in self._typeconf:
            return str(self._typeconf["device_class"])

        return None

    @property
    def unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the sensor."""
        if "unit" in self._typeconf:
            return str(self._typeconf["unit"])

        return None


class NefitYearTotal(NefitSensor):
    """Representation of the total year consumption."""

    @property
    def state(self) -> str | None:
        """Return the state/value of the sensor."""
        data = self.coordinator.data.get(self._key)

        if data is None:
            return None

        return "{:.1f}".format(
            data * 0.12307692
        )  # convert kWh to m3, for LPG, multiply with 0.040742416


class NefitStatus(NefitSensor):
    """Representation of the boiler status."""

    @property
    def state(self) -> str:
        """Return the state/value of the sensor."""
        return get_status(self.coordinator.data.get(self._key))


def get_status(code: str) -> str:
    """Return status of sensor."""
    display_codes = {
        "-H": "-H: central heating active",
        "=H": "=H: hot water active",
        "0C": "0C: system starting",
        "0L": "0L: system starting",
        "0U": "0U: system starting",
        "0E": "0E: system waiting",
        "0H": "0H: system standby",
        "0A": "0A: system waiting (boiler cannot transfer heat to central heating)",
        "0Y": "0Y: system waiting (boiler cannot transfer heat to central heating)",
        "2E": "2E: boiler water pressure too low",
        "H07": "H07: boiler water pressure too low",
        "2F": "2F: sensors measured abnormal temperature",
        "2L": "2L: sensors measured abnormal temperature",
        "2P": "2P: sensors measured abnormal temperature",
        "2U": "2U: sensors measured abnormal temperature",
        "4F": "4F: sensors measured abnormal temperature",
        "4L": "4L: sensors measured abnormal temperature",
        "6A": "6A: burner doesn't ignite",
        "6C": "6C: burner doesn't ignite",
        "rE": "rE: system restarting",
    }
    if code in display_codes:
        return display_codes[code]

    return code
