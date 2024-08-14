"""Tests of the nefiteasy sensor integration."""
from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed


async def test_disabled_sensor_default(hass: HomeAssistant, nefit_wrapper):
    """Test disabled state of entity."""
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("sensor.hot_water_operation")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("sensor.inhouse_temperature")
    assert entry
    assert entry.disabled is True


async def test_sensor_states(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, nefit_wrapper
):
    """Test sensor states for default enabled sensors."""
    freezer.tick(timedelta(seconds=65))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get("sensor.year_total")
    assert state
    assert state.state == "1227.1"

    state = hass.states.get("sensor.status")
    assert state
    assert state.state == "0E: system waiting"

    state = hass.states.get("sensor.supply_temperature")
    assert state
    assert state.state == "29.1"

    state = hass.states.get("sensor.outdoor_temperature")
    assert state
    assert state.state == "9.0"

    state = hass.states.get("sensor.system_pressure")
    assert state
    assert state.state == "1.5"

    state = hass.states.get("sensor.system_pressure")
    assert state
    assert state.state == "1.5"


async def test_sensor_states_disabled(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    nefit_sensor_wrapper,
    nefit_wrapper,
):
    """Test sensor states for default disabled sensors."""
    freezer.tick(timedelta(seconds=65))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get("sensor.nefiteasy_123456789_hot_water_operation")
    assert state
    assert state.state == "custom"

    state = hass.states.get("sensor.nefiteasy_123456789_inhouse_temperature")
    assert state
    assert state.state == "17.5"
