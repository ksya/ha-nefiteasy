"""Support for Bosch home thermostats."""
from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any
from datetime import datetime, timedelta

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NefitEasy
from .const import DOMAIN, SWITCHES
from .models import NefitSwitchEntityDescription
from .nefit_entity import NefitEntity
from .climate import OPERATION_CLOCK

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

    for description in SWITCHES:
        if description.key == "hot_water":
            entities.append(NefitHotWater(description, client, data))
        elif description.key == "holiday_mode":
            entities.append(NefitHolidayMode(description, client, data, config_entry))
        elif description.key == "lockui":
            entities.append(NefitSwitch(description, client, data, "true", "false"))
        elif description.key == "weather_dependent":
            entities.append(NefitSwitch(description, client, data, "weather", "room"))
        elif description.key == "home_entrance_detection":
            await setup_home_entrance_detection(
                entities,
                client,
                data,
                description.key,
                description.name,
                description.icon,
            )
        else:
            entities.append(NefitSwitch(description, client, data))

    async_add_entities(entities, True)


async def setup_home_entrance_detection(
    entities: list[NefitEntity],
    client: NefitEasy,
    data: MappingProxyType[str, Any],
    basekey: str,
    basename: str,
    baseicon: str,
) -> None:
    """Home entrance detection setup."""
    for i in range(0, 10):
        endpoint = "/ecus/rrc/homeentrancedetection"
        name = await client.async_init_presence(endpoint, i)

        if name is not None:
            description = NefitSwitchEntityDescription(
                key=f"presence{i}_detected",
                name=basename.format(name),
                url=f"{endpoint}/userprofile{i}/detected",
                icon=baseicon,
            )
            entities.append(NefitSwitch(description, client, data))


class NefitSwitch(NefitEntity, SwitchEntity):
    """Representation of a NefitSwitch entity."""

    entity_description: NefitSwitchEntityDescription

    def __init__(
        self,
        entity_description: NefitSwitchEntityDescription,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
        on_value: str = "on",
        off_value: str = "off",
    ) -> None:
        """Init Nefit Switch."""
        super().__init__(entity_description, client, data)

        self._on_value = on_value
        self._off_value = off_value

    @property
    def is_on(self) -> bool:
        """Get whether the switch is in on state."""
        return bool(
            self.coordinator.data.get(self.entity_description.key) == self._on_value
        )

    @property
    def assumed_state(self) -> bool:
        """Return true if we do optimistic updates."""
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._client.nefit.put_value(self.get_endpoint(), self._on_value)

        self._client.nefit.get(self.get_endpoint())

        _LOGGER.debug(
            "Switch Nefit %s to %s, endpoint=%s.",
            self.entity_description.key,
            self._on_value,
            self.get_endpoint(),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self._client.nefit.put_value(self.get_endpoint(), self._off_value)

        self._client.nefit.get(self.get_endpoint())

        _LOGGER.debug(
            "Switch Nefit %s to %s, endpoint=%s.",
            self.entity_description.key,
            self._off_value,
            self.get_endpoint(),
        )


class NefitHotWater(NefitSwitch):
    """Class for nefit hot water entity."""

    def get_endpoint(self) -> str:
        """Get end point."""
        endpoint = (
            "dhwOperationClockMode"
            if self.coordinator.data.get("user_mode") == "clock"
            else "dhwOperationManualMode"
        )
        return "/dhwCircuits/dhwA/" + endpoint


class NefitHolidayMode(NefitSwitch):
    """Class for nefit holiday mode entity.

       Note it only works if the thermostat preset is set to Clock
    """

    climate_entity = None
    climate_preset = None
    config_entry   = None

    def __init__(
        self,
        entity_description: NefitEntityDescription,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(entity_description, client, data)

        self.config_entry = config_entry

    def get_climate_entity( self ):
        if self.climate_entity is None:
            self.climate_entity = self.hass.data[DOMAIN][self.config_entry.entry_id][ "climate" ]

        return self.climate_entity

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""

        # Save and current preset mode and change it to Clock
        self.climate_preset = self.get_climate_entity().preset_mode

        _LOGGER.debug(
            "Forcing thermostat preset mode to %s, previous mode %s.",
            OPERATION_CLOCK,
            self.climate_preset,
        )

        await self.get_climate_entity().async_set_preset_mode(OPERATION_CLOCK)

        _LOGGER.info(
            "Thermostat preset mode set to %s during Holiday mode operation.",
            OPERATION_CLOCK,
        )

        holiday_start_ep = "/heatingCircuits/hc1/holidayMode/start"
        holiday_end_ep   = "/heatingCircuits/hc1/holidayMode/end"

        holiday_start_time = datetime.now().strftime("%Y-%m-%dT00:00:00")

        # Add 6 months
        holiday_end_time = ( datetime.now() + timedelta(days=180) ).strftime("%Y-%m-%dT00:00:00")

        _LOGGER.debug(
            "Setting holiday end date to %s, endpoint=%s.",
            holiday_end_time,
            holiday_end_ep,
        )

        self._client.nefit.put_value( holiday_end_ep, holiday_end_time)

        _LOGGER.debug(
            "Setting holiday start date to %s, endpoint=%s.",
            holiday_start_time,
            holiday_start_ep,
        )

        self._client.nefit.put_value( holiday_start_ep, holiday_start_time)

        _LOGGER.info(
            "Holiday mode starts from %s, and until %s.",
            holiday_start_time,
            holiday_end_time,
        )

        await super().async_turn_on( **kwargs )

        self._client.nefit.put_value( "/heatingCircuits/hc1/holidayMode/activated", self._on_value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""

        self._client.nefit.put_value( "/heatingCircuits/hc1/holidayMode/activated", self._off_value)

        await super().async_turn_off( **kwargs )

        # Setting the preset mode back to original
        if self.climate_preset is not None:
            await self.get_climate_entity().async_set_preset_mode(self.climate_preset)

            _LOGGER.info(
                "Thermostat preset restored to %s after Holiday mode operation was cancelled.",
                self.climate_preset,
            )

            self.climate_preset = None
