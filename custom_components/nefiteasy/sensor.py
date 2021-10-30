"""Support for Bosch home thermostats."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, SENSORS
from .models import NefitSensorEntityDescription
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

    for description in SENSORS:
        if description.key == "status":
            entities.append(NefitStatus(description, client, data))
        elif description.key == "year_total":
            entities.append(NefitYearTotal(description, client, data))
        else:
            entities.append(NefitSensor(description, client, data))

    async_add_entities(entities, True)


class NefitSensor(NefitEntity, SensorEntity):
    """Representation of a NefitSensor entity."""

    entity_description: NefitSensorEntityDescription

    @property
    def native_value(self) -> StateType:
        # def state(self) -> Any:
        """Return the state/value of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the sensor."""
        return self.entity_description.unit


class NefitYearTotal(NefitSensor):
    """Representation of the total year consumption."""

    @property
    def native_value(self) -> StateType:
        # def state(self) -> str | None:
        """Return the state/value of the sensor."""
        data = self.coordinator.data.get(self.entity_description.key)

        if data is None:
            return None

        return "{:.1f}".format(
            data * 0.12307692
        )  # convert kWh to m3, for LPG, multiply with 0.040742416


class NefitStatus(NefitSensor):
    """Representation of the boiler status."""

    @property
    def native_value(self) -> StateType:
        """Return the state/value of the sensor."""
        return get_status(self.coordinator.data.get(self.entity_description.key))


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
