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
            entities.append(NefitSwitch(client, data, key, typeconf, "true", "false"))
        elif key == "weather_dependent":
            entities.append(NefitSwitch(client, data, key, typeconf, "weather", "room"))
        elif key == "home_entrance_detection":
            await setup_home_entrance_detection(entities, client, data, key, typeconf)
        else:
            entities.append(NefitSwitch(client, data, key, typeconf))

    async_add_entities(entities, True)


async def setup_home_entrance_detection(entities, client, data, basekey, basetypeconf):
    """Home entrance detection setup."""
    for i in range(0, 10):
        endpoint = "/ecus/rrc/homeentrancedetection"
        name = await client.async_init_presence(endpoint, i)

        if name is not None:
            typeconf = {}
            typeconf["name"] = basetypeconf["name"].format(name)
            typeconf["url"] = f"{endpoint}/userprofile{i}/detected"
            typeconf["icon"] = basetypeconf["icon"]
            entities.append(
                NefitSwitch(client, data, f"presence{i}_detected", typeconf)
            )


class NefitSwitch(NefitEntity, SwitchEntity):
    """Representation of a NefitSwitch entity."""

    def __init__(self, client, data, key, typeconf, on_value="on", off_value="off"):
        """Init Nefit Switch."""
        super().__init__(client, data, key, typeconf)

        self._on_value = on_value
        self._off_value = off_value

    @property
    def is_on(self):
        """Get whether the switch is in on state."""
        return self.coordinator.data.get(self._key) == self._on_value

    @property
    def assumed_state(self) -> bool:
        """Return true if we do optimistic updates."""
        return False

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self.coordinator.nefit.put_value(self.get_endpoint(), self._on_value)

        self.coordinator.nefit.get(self.get_endpoint())

        _LOGGER.debug(
            "Switch Nefit %s to %s, endpoint=%s.",
            self._key,
            self._on_value,
            self.get_endpoint(),
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self.coordinator.nefit.put_value(self.get_endpoint(), self._off_value)

        self.coordinator.nefit.get(self.get_endpoint())

        _LOGGER.debug(
            "Switch Nefit %s to %s, endpoint=%s.",
            self._key,
            self._off_value,
            self.get_endpoint(),
        )


class NefitHotWater(NefitSwitch):
    """Class for nefit hot water entity."""

    def get_endpoint(self):
        """Get end point."""
        endpoint = (
            "dhwOperationClockMode"
            if self.coordinator.data.get("user_mode") == "clock"
            else "dhwOperationManualMode"
        )
        return "/dhwCircuits/dhwA/" + endpoint
