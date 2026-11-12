"""Data update coordinator for Nefit Easy."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import re
from typing import Any

from aionefit import NefitCore
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .connection import NefitConnection
from .const import DOMAIN, STATE_INIT, short
from .models import NefitEntityDescription

_LOGGER = logging.getLogger(__name__)


class NefitEasy(DataUpdateCoordinator):
    """Supporting class for nefit easy."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize nefit easy component."""
        _LOGGER.debug("Initialize Nefit class")

        self._data: dict[str, Any] = {}  # stores device states and values
        self._lock = asyncio.Lock()
        self.hass = hass
        self._config = config

        self.connection = NefitConnection(
            config,
            message_callback=self.parse_message,
            session_lost_callback=self._session_lost,
            auth_failed_callback=self._auth_failed,
        )
        self.serial = self.connection.serial

        self._urls: dict[str, Any] = {}
        self._status_keys: dict[str, Any] = {}

        update_interval = timedelta(seconds=60)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    @property
    def nefit(self) -> NefitCore:
        """The NefitCore client, for entities that send commands."""
        return self.connection.nefit

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

    def _session_lost(self) -> None:
        """Schedule an immediate reconnect rather than waiting up to 60s for the next poll."""
        self.hass.async_create_task(self.async_refresh())

    async def _auth_failed(self, event: str) -> None:
        """Tell the user and start reauthentication."""
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

    async def parse_message(self, data: dict[str, Any]) -> None:
        """Message received callback function for the XMPP client."""
        verified = self.connection.verified
        if data["id"] == "/ecus/rrc/uiStatus" and verified:
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
            and verified
        ):
            m = re.search(r"(?<=userprofile)\w+", data["id"])
            if m is not None:
                id = m.group(0)

                val = data["id"].rsplit("/", 1)[-1]

                self._data[f"presence{id}_{val}"] = data["value"]
        elif data["id"] in self._urls and verified:
            self._data[self._urls[data["id"]]["key"]] = data["value"]
        else:
            return

        if not self.connection.resolve(data["id"]):
            self.async_set_updated_data(self._data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        if not self.connection.verified:
            _LOGGER.debug("Starting reconnect procedure.")
            await self.connection.connect()
            if not self.connection.verified:
                raise UpdateFailed("Nefit easy not connected!")

        async with self._lock:
            try:
                _url = "/ecus/rrc/uiStatus"
                await self.connection.async_get(_url)

                for _url in self._urls:
                    await self.connection.async_get(_url)
            except Exception as ex:
                _LOGGER.warning(
                    "Nefit Easy communication error on %s, resetting "
                    "connection state: %r",
                    _url,
                    ex,
                )
                self.connection.connected_state = STATE_INIT
                raise UpdateFailed(
                    f"Error communicating with Nefit Easy on {_url}: {ex!r}"
                ) from ex

        return self._data

    async def async_init_presence(self, endpoint: str, index: int) -> Any:
        """Init presence detection."""
        async with self._lock:
            url = f"{endpoint}/userprofile{index}/active"
            await self.connection.async_get(url)

            if self._data[f"presence{index}_active"] == "on":
                url = f"{endpoint}/userprofile{index}/name"
                await self.connection.async_get(url)

                return self._data.get(f"presence{index}_name")

            return None

    async def update_ui_status_later(self, delay: float) -> None:
        """Force update of uiStatus after delay."""
        self.hass.loop.call_later(delay, self.nefit.get, "/ecus/rrc/uiStatus")
