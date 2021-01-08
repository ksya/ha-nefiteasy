"""Support for Bosch home thermostats."""

import logging

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN, SWITCH_TYPES
from .nefit_entity import NefitEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Switch setup for nefit easy."""
    entities = []

    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    data = config_entry.data

    for key in SWITCH_TYPES:
        typeconf = SWITCH_TYPES[key]
        if key == "hot_water":
            entities.append(NefitHotWater(client, data, key, typeconf))
        elif key == "lockui":
            entities.append(NefitSwitchTrueFalse(client, data, key, typeconf))
        elif key == "weather_dependent":
            entities.append(NefitWeatherDependent(client, data, key, typeconf))
        elif key == "home_entrance_detection":
            continue
        #    await setup_home_entrance_detection(entities, client, data, key, typeconf)
        else:
            entities.append(NefitSwitch(client, data, key, typeconf))

    async_add_entities(entities, True)


async def setup_home_entrance_detection(entities, client, data, basekey, basetypeconf):
    """Home entrance detection setup."""
    for i in range(0, 10):
        if f"presence{i}_name" in client.coordinator.data:
            name = client.coordinator.data[f"presence{i}_name"]
            endpoint = f"/ecus/rrc/homeentrancedetection/userprofile{i}/detected"

            typeconf = {}
            typeconf["name"] = basetypeconf["name"].format(name)
            typeconf["url"] = endpoint
            typeconf["icon"] = basetypeconf["icon"]

            entities.append(
                NefitSwitch(client, data, f"presence{i}_detected", typeconf)
            )


class NefitSwitch(NefitEntity, SwitchEntity):
    """Representation of a NefitSwitch entity."""

    @property
    def is_on(self):
        """Get whether the switch is in on state."""
        return self.coordinator.data.get(self._key) == "on"

    @property
    def assumed_state(self) -> bool:
        """Return true if we do optimistic updates."""
        return False

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self.coordinator.nefit.put_value(self.get_endpoint(), "on")

        _LOGGER.debug(
            "Switch Nefit %s ON, endpoint=%s.", self._key, self.get_endpoint()
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self.coordinator.nefit.put_value(self.get_endpoint(), "off")

        _LOGGER.debug(
            "Switch Nefit %s OFF, endpoint=%s.", self._key, self.get_endpoint()
        )


class NefitHotWater(NefitSwitch):
    """Class for nefit hot water entity."""

    def __init__(self, client, data, key, typeconf):
        """Initialize the switch."""
        super().__init__(client, data, key, typeconf)

    def get_endpoint(self):
        """Get end point."""
        endpoint = (
            "dhwOperationClockMode"
            if self.coordinator.data.get("user_mode") == "clock"
            else "dhwOperationManualMode"
        )
        return "/dhwCircuits/dhwA/" + endpoint


class NefitWeatherDependent(NefitSwitch):
    """Class for nefit weather dependent entity."""

    @property
    def is_on(self):
        """Get whether the switch is in on state."""
        return self.coordinator.data.get(self._key) == "weather"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self.coordinator.nefit.put_value(self.get_endpoint(), "weather")

        _LOGGER.debug("Switch weather dependent ON, endpoint=%s.", self.get_endpoint())

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self.coordinator.nefit.put_value(self.get_endpoint(), "room")

        _LOGGER.debug("Switch weather dependent OFF, endpoint=%s.", self.get_endpoint())


class NefitSwitchTrueFalse(NefitEntity, SwitchEntity):
    """Class for nefit true/false entity."""

    @property
    def is_on(self):
        """Get whether the switch is in on state."""
        return self.coordinator.data.get(self._key) == "true"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self.coordinator.nefit.put_value(self.get_endpoint(), "true")

        _LOGGER.debug(
            "Switch Nefit %s ON, endpoint=%s.", self._key, self.get_endpoint()
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self.coordinator.nefit.put_value(self.get_endpoint(), "false")

        _LOGGER.debug(
            "Switch Nefit %s OFF, endpoint=%s.", self._key, self.get_endpoint()
        )
