"""Support for Bosch home thermostats."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NefitEasy
from .const import DOMAIN, ENDPOINT_HOLIDAY_MODE_BASE, ENDPOINT_UI_STATUS, SWITCHES
from .models import NefitSwitchEntityDescription
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

    for description in SWITCHES:
        if description.key == "hot_water":
            entities.append(NefitHotWater(description, client, data))
        elif description.key == "holiday_mode":
            entities.append(NefitHolidayMode(description, client, data))
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

    climate_saved_preset = None
    climate_saved_setpoint = None
    climate_clock_preset = "clock"

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new target operation mode."""
        _LOGGER.debug("Holiday mode set_preset_mode called mode=%s", preset_mode)

        self._client.nefit.set_usermode(preset_mode)
        await asyncio.wait_for(
            self._client.nefit.xmppclient.message_event.wait(), timeout=9
        )
        self._client.nefit.xmppclient.message_event.clear()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""

        # Save and current preset mode and change it to Clock
        self.climate_saved_preset = (
            self._client._data["user_mode"]
            if self._client._data["user_mode"] != self.climate_clock_preset
            else None
        )
        self.climate_saved_setpoint = self._client._data["temp_setpoint"]

        if self.climate_saved_preset is not None:
            _LOGGER.debug(
                "Forcing thermostat preset mode to %s, previous mode %s, previous setpoint %s.",
                self.climate_clock_preset,
                self.climate_saved_preset,
                self.climate_saved_setpoint,
            )

            await self.async_set_preset_mode(self.climate_clock_preset)

            _LOGGER.info(
                "Thermostat preset mode set to %s during Holiday mode operation.",
                self.climate_clock_preset,
            )

        holiday_start_ep = ENDPOINT_HOLIDAY_MODE_BASE + "/start"
        holiday_end_ep = ENDPOINT_HOLIDAY_MODE_BASE + "/end"
        holiday_start_time = datetime.now().strftime("%Y-%m-%dT00:00:00")

        # Add 6 months
        holiday_end_time = (datetime.now() + timedelta(days=180)).strftime(
            "%Y-%m-%dT00:00:00"
        )

        _LOGGER.debug(
            "Setting holiday end date to %s, endpoint=%s.",
            holiday_end_time,
            holiday_end_ep,
        )

        self._client.nefit.put_value(holiday_end_ep, holiday_end_time)

        _LOGGER.debug(
            "Setting holiday start date to %s, endpoint=%s.",
            holiday_start_time,
            holiday_start_ep,
        )

        self._client.nefit.put_value(holiday_start_ep, holiday_start_time)

        _LOGGER.info(
            "Holiday mode starts from %s, and until %s.",
            holiday_start_time,
            holiday_end_time,
        )

        await super().async_turn_on(**kwargs)

        self._client.nefit.get(ENDPOINT_UI_STATUS)
        await self._client.update_ui_status_later(2)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""

        await super().async_turn_off(**kwargs)

        # Setting the preset mode back to original
        if self.climate_saved_preset is not None:
            await self.async_set_preset_mode(self.climate_saved_preset)

            _LOGGER.info(
                "Thermostat preset restored to %s after Holiday mode operation was cancelled.",
                self.climate_saved_preset,
            )

            self.climate_saved_preset = None

        if self.climate_saved_setpoint is not None:
            self._client.nefit.set_temperature(self.climate_saved_setpoint)
            await asyncio.wait_for(
                self._client.nefit.xmppclient.message_event.wait(), timeout=9
            )
            self._client.nefit.xmppclient.message_event.clear()

            _LOGGER.info(
                "Thermostat setpoint restored to %s after Holiday mode operation was cancelled.",
                self.climate_saved_setpoint,
            )

            self.climate_saved_setpoint = None

        self._client.nefit.get(ENDPOINT_UI_STATUS)
        await self._client.update_ui_status_later(2)
