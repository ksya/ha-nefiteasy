"""Support for Bosch home thermostats."""

import asyncio
import logging
from typing import Dict

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    HVAC_MODE_HEAT,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Climate setup for nefit easy."""
    entities = []

    client = hass.data[DOMAIN][config_entry.entry_id]["client"]

    entities.append(NefitThermostat(client, config_entry.data))

    async_add_entities(entities, update_before_add=True)


class NefitThermostat(CoordinatorEntity, ClimateEntity):
    """Representation of a NefitThermostat device."""

    def __init__(self, client, data):
        """Initialize the thermostat."""
        super().__init__(client)

        self._config = data
        self._unique_id = "{}_{}".format(client.nefit.serial_number, "climate")

        self._unit_of_measurement = TEMP_CELSIUS
        self._hvac_modes = [HVAC_MODE_HEAT]

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def target_temperature_step(self):
        """Return target temperature step."""
        return self._config[CONF_TEMP_STEP]

    @property
    def name(self):
        """Return the name of the ClimateEntity."""
        return self._config[CONF_NAME]

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.coordinator.data.get("inhouse_temperature")

    @property
    def target_temperature(self):
        """Return target temperature."""
        return self.coordinator.data.get("temp_setpoint")

    @property
    def hvac_modes(self):
        """List of available modes."""
        return self._hvac_modes

    @property
    def hvac_mode(self):
        """Return hvac mode."""
        return HVAC_MODE_HEAT

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        if (
            self.coordinator.data.get("boiler_indicator") == "CH"
        ):  # HW (hot water) is not for climate
            return CURRENT_HVAC_HEAT

        return CURRENT_HVAC_IDLE

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return [OPERATION_MANUAL, OPERATION_CLOCK]

    @property
    def preset_mode(self):
        """Return the current preset mode."""
        if self.coordinator.data.get("user_mode") == "manual":
            return OPERATION_MANUAL
        if self.coordinator.data.get("user_mode") == "clock":
            return OPERATION_CLOCK

        return OPERATION_MANUAL

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        return {
            "last_update": self.coordinator.data.get("last_update"),
            "boiler_indicator": self.coordinator.data.get("boiler_indicator"),
        }

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._config[CONF_MIN_TEMP]

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._config[CONF_MAX_TEMP]

    @property
    def device_info(self) -> Dict[str, any]:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._config[CONF_SERIAL])},
            "name": self._config[CONF_NAME],
            "manufacturer": "Bosch",
        }

    async def async_set_preset_mode(self, preset_mode):
        """Set new target operation mode."""
        _LOGGER.debug("set_preset_mode called mode=%s", preset_mode)
        if preset_mode == OPERATION_CLOCK:
            new_mode = "clock"
        else:
            new_mode = "manual"

        self.coordinator.nefit.set_usermode(new_mode)
        await asyncio.wait_for(
            self.coordinator.nefit.xmppclient.message_event.wait(), timeout=9
        )
        self.coordinator.nefit.xmppclient.message_event.clear()

        self.coordinator.nefit.get("/ecus/rrc/uiStatus")
        await self.coordinator.update_ui_status_later(2)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("set_temperature called (temperature=%s)", temperature)
        self.coordinator.nefit.set_temperature(temperature)
        await asyncio.wait_for(
            self.coordinator.nefit.xmppclient.message_event.wait(), timeout=9
        )
        self.coordinator.nefit.xmppclient.message_event.clear()

        self.coordinator.nefit.get("/ecus/rrc/uiStatus")
