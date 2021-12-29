"""Tests of the nefiteasy number integration."""
from datetime import timedelta

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from homeassistant.components.number.const import ATTR_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.dt import utcnow

from tests.common import async_fire_time_changed


async def test_disabled_number_default(hass: HomeAssistant, nefit_wrapper):
    """Test disabled state of entity."""
    entity_id = "number.shower_timer_duration"

    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.disabled is True


async def test_shower_timer(hass: HomeAssistant, nefit_number_wrapper, nefit_wrapper):
    """Test setup of climate entity."""
    entity_id = "number.nefiteasy_123456789_shower_timer_duration"

    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get(entity_id)
    assert entry

    async_fire_time_changed(hass, utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state
    assert state.state == "20"

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 5},
        blocking=True,
    )
    await hass.async_block_till_done()

    async_fire_time_changed(hass, utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state
    assert state.state == "5.0"
