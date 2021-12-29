"""Tests of the nefiteasy climate integration."""
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.components.climate.const import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_PRESET_MODE,
    HVAC_MODE_HEAT,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_climate_device(hass: HomeAssistant, nefit_wrapper):
    """Test setup of climate entity."""
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("climate.nefit")
    assert entry

    thermostat = hass.states.get("climate.nefit")
    assert thermostat
    assert thermostat.state == HVAC_MODE_HEAT
    assert thermostat.attributes[ATTR_PRESET_MODE] == "Clock"
    assert thermostat.attributes[ATTR_TEMPERATURE] == 20.0
    assert thermostat.attributes[ATTR_CURRENT_TEMPERATURE] == 17.50


async def test_climate_set_temperature(hass: HomeAssistant, nefit_wrapper):
    """Test setting up temperature on climate entity."""
    nefit_climate_entity = "climate.nefit"

    thermostat = hass.states.get("climate.nefit")
    assert thermostat.attributes[ATTR_TEMPERATURE] == 20.0

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {"entity_id": nefit_climate_entity, ATTR_TEMPERATURE: 17.0},
        blocking=True,
    )
    await hass.async_block_till_done()

    thermostat = hass.states.get("climate.nefit")
    assert thermostat.attributes[ATTR_TEMPERATURE] == 17.0


async def test_climate_set_mode(hass: HomeAssistant, nefit_wrapper):
    """Test setting mode on climate entity."""
    nefit_climate_entity = "climate.nefit"

    thermostat = hass.states.get("climate.nefit")
    assert thermostat
    assert thermostat.state == HVAC_MODE_HEAT
    assert thermostat.attributes[ATTR_PRESET_MODE] == "Clock"
    assert thermostat.attributes["boiler_indicator"] == "CH"
    assert thermostat.attributes["last_update"] == "2021-12-28T21:43:25+00:00 Tu"

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {
            ATTR_ENTITY_ID: nefit_climate_entity,
            ATTR_PRESET_MODE: "Manual",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    thermostat = hass.states.get("climate.nefit")
    assert thermostat
    assert thermostat.state == HVAC_MODE_HEAT
    assert thermostat.attributes[ATTR_PRESET_MODE] == "Manual"

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {
            ATTR_ENTITY_ID: nefit_climate_entity,
            ATTR_PRESET_MODE: "Clock",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    thermostat = hass.states.get("climate.nefit")
    assert thermostat
    assert thermostat.state == HVAC_MODE_HEAT
    assert thermostat.attributes[ATTR_PRESET_MODE] == "Clock"
