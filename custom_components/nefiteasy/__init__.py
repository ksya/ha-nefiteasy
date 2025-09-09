"""Support for first generation Bosch smart home thermostats: Nefit Easy, Junkers CT100 etc."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import re
from typing import Any

from aionefit import NefitCore
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import slixmpp

from .const import (
    CONF_ACCESSKEY,
    CONF_PASSWORD,
    CONF_SERIAL,
    DOMAIN,
    ENDPOINT_UI_STATUS,
    STATE_CONNECTED,
    STATE_CONNECTION_VERIFIED,
    STATE_ERROR_AUTH,
    STATE_INIT,
    short,
)
from .models import NefitEntityDescription

_LOGGER = logging.getLogger(__name__)


DOMAINS = ["climate", "select", "sensor", "switch", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the nefiteasy component."""
    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {}

    credentials = dict(entry.data)
    client = NefitEasy(hass, credentials)

    await client.connect()
    if client.connected_state == STATE_CONNECTION_VERIFIED:
        hass.data[DOMAIN][entry.entry_id]["client"] = client
    else:
        raise ConfigEntryNotReady

    await hass.config_entries.async_forward_entry_setups(entry, DOMAINS)

    await client.async_refresh()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload nefit easy component."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, DOMAINS)

    if unload_ok:
        client = hass.data[DOMAIN][entry.entry_id]["client"]

        await client.shutdown("Unload entry")

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class NefitEasy(DataUpdateCoordinator):
    """Supporting class for nefit easy."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize nefit easy component."""
        _LOGGER.debug("Initialize Nefit class")

        self._data: dict[str, Any] = {}  # stores device states and values
        self._event = asyncio.Event()
        self._lock = asyncio.Lock()
        self.hass = hass
        self.connected_state = STATE_INIT
        self.expected_end = False
        self.is_connecting = False
        self.serial = config[CONF_SERIAL]
        self._config = config
        self._request: str = ""

        self.nefit = NefitCore(
            serial_number=config[CONF_SERIAL],
            access_key=config[CONF_ACCESSKEY],
            password=config[CONF_PASSWORD],
            message_callback=self.parse_message,
        )

        self.nefit.failed_auth_handler = self.failed_auth_handler
        self.nefit.no_content_callback = self.no_content_callback
        self.nefit.session_end_callback = self.session_end_callback

        self._urls: dict[str, Any] = {}
        self._status_keys: dict[str, Any] = {}

        update_interval = timedelta(seconds=60)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def add_key(self, entity_description: NefitEntityDescription) -> None:
        """Add key to list of endpoints."""
        async with self._lock:
            if entity_description.url is not None:
                self._urls[entity_description.url] = {
                    "key": entity_description.key,
                    short: entity_description.short,
                }
            elif entity_description.short is not None:
                self._status_keys[entity_description.short] = entity_description.key

    async def connect(self) -> None:
        """Connect to nefit easy."""
        _LOGGER.debug("Start connecting.")
        if not self.is_connecting:
            _LOGGER.debug("Set is connecting to true")
            self.is_connecting = True

            await self.nefit.connect()
            _LOGGER.debug("Waiting for connected event.")
            try:
                await asyncio.wait_for(
                    self.nefit.xmppclient.connected_event.wait(), timeout=29.0
                )
            except asyncio.TimeoutError:
                _LOGGER.debug("TimeoutError on waiting for connected event.")
            except:  # noqa: E722 pylint: disable=bare-except
                _LOGGER.debug("Unknown error.")
            else:
                _LOGGER.debug("Connected successfully.")
                self.connected_state = STATE_CONNECTED

            if self.connected_state == STATE_CONNECTED:
                try:
                    self.nefit.get("/gateway/brandID")
                except slixmpp.xmlstream.xmlstream.NotConnectedError:
                    self.connected_state == STATE_INIT
                    _LOGGER.debug("Set is connecting to false")
                    self.is_connecting = False
                    return

                try:
                    _LOGGER.debug("Wait for message event")

                    await asyncio.wait_for(
                        self.nefit.xmppclient.message_event.wait(), timeout=29.0
                    )
                except asyncio.TimeoutError:
                    _LOGGER.debug(
                        "Did not get a response in time for testing connection."
                    )
                except:  # noqa: E722 pylint: disable=bare-except
                    _LOGGER.debug("No connection while testing connection.")
                else:
                    _LOGGER.debug("Message event received")

                    self.nefit.xmppclient.message_event.clear()

                    # No exception and no auth error
                    if self.connected_state == STATE_CONNECTED:
                        self.connected_state = STATE_CONNECTION_VERIFIED

            if self.connected_state != STATE_CONNECTION_VERIFIED:
                _LOGGER.debug("Successfully verified connection.")

            _LOGGER.debug("Set is connecting to false")
            self.is_connecting = False
        else:
            _LOGGER.debug("Connection procedure is already running.")

    async def shutdown(self, event: str) -> None:
        """Shutdown."""
        _LOGGER.debug("Shutdown connection to Bosch cloud")
        self.expected_end = True
        await self.nefit.disconnect()

    async def no_content_callback(self, data: Any) -> None:
        """Log no content."""
        _LOGGER.debug("no_content_callback: %s", data)

    async def failed_auth_handler(self, event: str) -> None:
        """Handle failed auth."""
        self.connected_state = STATE_ERROR_AUTH
        self.nefit.xmppclient.connected_event.set()

        # disconnect, since nothing will work from now.
        await self.shutdown("auth_failed")

        if event == "auth_error_password":
            self.hass.components.persistent_notification.create(
                f"Invalid password for connecting {self.serial} to Bosch cloud.",
                title="Nefit password error",
                notification_id="nefit_password_error",
            )
        else:
            self.hass.components.persistent_notification.create(
                f"Invalid credentials (serial or accesskey) for connecting {self.serial} to Bosch cloud.",
                title="Nefit authentication error",
                notification_id="nefit_logon_error",
            )

        if self.config_entry:
            self.config_entry.async_start_reauth(self.hass)

    async def session_end_callback(self) -> None:
        """If connection is closed unexpectedly, try to reconnect."""
        if not self.expected_end:
            _LOGGER.debug(
                f"Unexpected disconnect of {self.serial} with Bosch server. Try to reconnect.."
            )

            # Reset values
            self.connected_state = STATE_INIT
            self.expected_end = False

    async def parse_message(self, data: dict[str, Any]) -> None:
        """Message received callback function for the XMPP client."""
        if (
            data["id"] == ENDPOINT_UI_STATUS
            and self.connected_state == STATE_CONNECTION_VERIFIED
        ):
            self._data["temp_setpoint"] = float(data["value"]["TSP"])  # for climate
            self._data["inhouse_temperature"] = float(
                data["value"]["IHT"]
            )  # for climate
            self._data["user_mode"] = data["value"]["UMD"]  # for climate
            self._data["boiler_indicator"] = data["value"]["BAI"]  # for climate
            self._data["last_update"] = data["value"]["CTD"]

            for val, key in self._status_keys.items():
                self._data[key] = data["value"].get(val)
        elif (
            data["id"].startswith("/ecus/rrc/homeentrancedetection/userprofile")
            and self.connected_state == STATE_CONNECTION_VERIFIED
        ):
            m = re.search(r"(?<=userprofile)\w+", data["id"])
            if m is not None:
                id = m.group(0)

                val = data["id"].rsplit("/", 1)[-1]

                self._data[f"presence{id}_{val}"] = data["value"]
        elif (
            data["id"] in self._urls
            and self.connected_state == STATE_CONNECTION_VERIFIED
        ):
            self._data[self._urls[data["id"]]["key"]] = data["value"]
        else:
            return

        if self._request == data["id"]:
            self._event.set()
        else:
            self.async_set_updated_data(self._data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        if self.connected_state != STATE_CONNECTION_VERIFIED:
            _LOGGER.debug("Starting reconnect procedure.")
            await self.connect()
            if self.connected_state != STATE_CONNECTION_VERIFIED:
                raise UpdateFailed("Nefit easy not connected!")

        async with self._lock:
            _url = ENDPOINT_UI_STATUS
            await self._async_get_url(_url)

            for _url in self._urls:
                await self._async_get_url(_url)

        return self._data

    async def async_init_presence(self, endpoint: str, index: int) -> Any:
        """Init presence detection."""
        async with self._lock:
            url = f"{endpoint}/userprofile{index}/active"
            await self._async_get_url(url)

            if self._data[f"presence{index}_active"] == "on":
                url = f"{endpoint}/userprofile{index}/name"
                await self._async_get_url(url)

                return self._data.get(f"presence{index}_name")

            return None

    async def update_ui_status_later(self, delay: float) -> None:
        """Force update of uiStatus after delay."""
        self.hass.loop.call_later(delay, self.nefit.get, ENDPOINT_UI_STATUS)

    async def _async_get_url(self, url: str) -> None:
        self._event.clear()
        self._request = url
        self.nefit.get(url)
        await asyncio.wait_for(self._event.wait(), timeout=9)
        self._request = ""
