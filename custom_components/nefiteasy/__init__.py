"""Support for first generation Bosch smart home thermostats: Nefit Easy, Junkers CT100 etc."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_SERIAL, DOMAIN
from .coordinator import NefitEasy

_LOGGER = logging.getLogger(__name__)


DOMAINS = ["climate", "select", "sensor", "switch", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the nefiteasy component."""
    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {}

    credentials = dict(entry.data)
    client = NefitEasy(hass, credentials)

    await client.connection.connect()
    if client.connection.verified:
        hass.data[DOMAIN][entry.entry_id]["client"] = client
    else:
        # Stop the client fully, otherwise slixmpp keeps retrying in the background
        # and Home Assistant's own setup retry starts a second client alongside it.
        await client.connection.shutdown("Setup failed")
        raise ConfigEntryNotReady(
            f"Unable to verify connection to {credentials[CONF_SERIAL]}, "
            f"state: {client.connection.connected_state}"
        )

    async def _async_on_stop(event: Event) -> None:
        await client.connection.shutdown("Home Assistant stopping")

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_on_stop)
    )

    # Fetch uiStatus before the platforms add their entities, so they never see
    # coordinator.data as None.
    await client.async_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, DOMAINS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload nefit easy component."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, DOMAINS)

    if unload_ok:
        client = hass.data[DOMAIN][entry.entry_id]["client"]

        await client.connection.shutdown("Unload entry")

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
