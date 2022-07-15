"""Models for the nefiteasy integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.helpers.entity import EntityDescription


@dataclass
class NefitEntityDescription(EntityDescription):
    """Represents an nefiteasy entity."""

    url: str | None = None
    short: str | None = None
    unit: str | None = None


@dataclass
class NefitSwitchEntityDescription(NefitEntityDescription, SwitchEntityDescription):
    """Represents a nefiteasy switch."""


@dataclass
class NefitSelectEntityDescription(NefitEntityDescription, SelectEntityDescription):
    """Represents a nefiteasy Select."""

    options: dict[int, Any] | None = None


@dataclass
class NefitSensorEntityDescription(NefitEntityDescription, SensorEntityDescription):
    """Represents a nefiteasy Sensor."""


@dataclass
class NefitNumberEntityDescription(NefitEntityDescription, NumberEntityDescription):
    """Represents a nefiteasy Number."""

    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
