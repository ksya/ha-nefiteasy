"""Tests of the nefiteasy sensor integration."""
from datetime import timedelta

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import async_fire_time_changed


async def test_disabled_switch_default(hass: HomeAssistant, nefit_wrapper):
    """Test disabled state of entity."""
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("switch.hot_water")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.holiday_mode")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.fireplace_mode")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.today_as_sunday")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.tomorrow_as_sunday")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.preheating")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.weather_dependent")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.lock_ui")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.shower_timer")
    assert entry
    assert entry.disabled is True


async def test_switch_states(hass: HomeAssistant, nefit_switch_wrapper, nefit_wrapper):
    """Test states of switches."""
    async_fire_time_changed(hass, utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()

    state = hass.states.get("switch.nefiteasy_123456789_hot_water")
    assert state
    assert state.state == "on"

    state = hass.states.get("switch.nefiteasy_123456789_holiday_mode")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_fireplace_mode")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_today_as_sunday")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_tomorrow_as_sunday")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_preheating")
    assert state
    assert state.state == "on"

    state = hass.states.get("switch.nefiteasy_123456789_weather_dependent")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_lockui")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_shower_timer")
    assert state
    assert state.state == "off"


async def test_switch_turn_on_off(
    hass: HomeAssistant, nefit_switch_wrapper, nefit_wrapper
):
    """Test states of switches."""
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.nefiteasy_123456789_holiday_mode"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get("switch.nefiteasy_123456789_holiday_mode")
    assert state
    assert state.state == "on"

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.nefiteasy_123456789_preheating"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get("switch.nefiteasy_123456789_preheating")
    assert state
    assert state.state == "off"


async def test_presence_detection(
    hass: HomeAssistant, nefit_config, nefit_wrapper_precense
):
    """Test presence detection."""
    client = nefit_wrapper_precense

    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("switch.presence_my_device")
    assert entry

    async_fire_time_changed(hass, utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()

    state = hass.states.get("switch.presence_my_device")
    assert state
    assert state.state == "on"

    client.data["/ecus/rrc/homeentrancedetection/userprofile1/detected"][
        "value"
    ] = "off"

    async_fire_time_changed(hass, utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()

    state = hass.states.get("switch.presence_my_device")
    assert state
    assert state.state == "off"
