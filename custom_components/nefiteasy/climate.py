"""Support for Bosch home thermostats."""
from __future__ import annotations

import asyncio
import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    HVAC_MODE_HEAT,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NefitEasy
from .const import (
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_NAME,
    CONF_SERIAL,
    CONF_TEMP_STEP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

# supported operating modes (preset mode)
OPERATION_MANUAL = "Manual"
OPERATION_CLOCK = "Clock"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Climate setup for nefit easy."""
    entities = []

    client = hass.data[DOMAIN][config_entry.entry_id]["client"]

    entities.append(NefitThermostat(client, config_entry.data))

    async_add_entities(entities, update_before_add=True)


class NefitThermostat(CoordinatorEntity, ClimateEntity):
    """Representation of a NefitThermostat device."""

    def __init__(self, client: NefitEasy, data: MappingProxyType[str, Any]) -> None:
        """Initialize the thermostat."""
        super().__init__(client)

        self._config = data
        self._client = client

        self._unit_of_measurement = TEMP_CELSIUS
        self._hvac_modes = [HVAC_MODE_HEAT]

        self._attr_unique_id = "{}_{}".format(client.nefit.serial_number, "climate")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._config[CONF_SERIAL])},
            "name": self._config[CONF_NAME],
            "manufacturer": "Bosch",
        }

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def target_temperature_step(self) -> float:
        """Return target temperature step."""
        return float(self._config[CONF_TEMP_STEP])

    @property
    def name(self) -> str:
        """Return the name of the ClimateEntity."""
        return str(self._config[CONF_NAME])

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return float(self.coordinator.data.get("inhouse_temperature"))

    @property
    def target_temperature(self) -> float:
        """Return target temperature."""
        return float(self.coordinator.data.get("temp_setpoint"))

    @property
    def hvac_modes(self) -> list[str]:
        """List of available modes."""
        return self._hvac_modes

    @property
    def hvac_mode(self) -> str:
        """Return hvac mode."""
        return HVAC_MODE_HEAT

    @property
    def hvac_action(self) -> str:
        """Return the current running hvac operation if supported."""
        if (
            self.coordinator.data.get("boiler_indicator") == "CH"
        ):  # HW (hot water) is not for climate
            return CURRENT_HVAC_HEAT

        return CURRENT_HVAC_IDLE

    @property
    def preset_modes(self) -> list[str]:
        """Return available preset modes."""
        return [OPERATION_MANUAL, OPERATION_CLOCK]

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode."""
        if self.coordinator.data.get("user_mode") == "manual":
            return OPERATION_MANUAL
        if self.coordinator.data.get("user_mode") == "clock":
            return OPERATION_CLOCK

        return OPERATION_MANUAL

    @property
    def device_state_attributes(self) -> dict[str, Any]:
        """Return the device specific state attributes."""
        return {
            "last_update": self.coordinator.data.get("last_update"),
            "boiler_indicator": self.coordinator.data.get("boiler_indicator"),
        }

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return float(self._config[CONF_MIN_TEMP])

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return float(self._config[CONF_MAX_TEMP])

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new target operation mode."""
        _LOGGER.debug("set_preset_mode called mode=%s", preset_mode)
        if preset_mode == OPERATION_CLOCK:
            new_mode = "clock"
        else:
            new_mode = "manual"

        self._client.nefit.set_usermode(new_mode)
        await asyncio.wait_for(
            self._client.nefit.xmppclient.message_event.wait(), timeout=9
        )
        self._client.nefit.xmppclient.message_event.clear()

        self._client.nefit.get("/ecus/rrc/uiStatus")
        await self._client.update_ui_status_later(2)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("set_temperature called (temperature=%s)", temperature)
        self._client.nefit.set_temperature(temperature)
        await asyncio.wait_for(
            self._client.nefit.xmppclient.message_event.wait(), timeout=9
        )
        self._client.nefit.xmppclient.message_event.clear()

        self._client.nefit.get("/ecus/rrc/uiStatus")
