"""Tests of the nefiteasy select integration."""
from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select.const import ATTR_OPTION
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed


async def test_disabled_select_default(hass: HomeAssistant, nefit_wrapper):
    """Test disabled state of entity."""
    entity_id = "select.active_program"

    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.disabled is True


async def test_active_program(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    nefit_select_wrapper,
    nefit_wrapper,
):
    """Test setup of select entity."""
    entity_id = "select.nefiteasy_123456789_active_program"

    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get(entity_id)
    assert entry

    freezer.tick(timedelta(seconds=65))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get(entity_id)
    assert state
    assert state.state == "Clock 1"

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_OPTION: "Clock 2",
        },
        blocking=True,
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    freezer.tick(timedelta(seconds=65))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get(entity_id)
    assert state.state == "Clock 2"
