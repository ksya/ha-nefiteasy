"""Support for first generation Bosch smart home thermostats: Nefit Easy, Junkers CT100 etc."""

import asyncio
from datetime import timedelta
import logging
import re

from aionefit import NefitCore
import voluptuous as vol

from homeassistant import config_entries

# from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ACCESSKEY,
    CONF_DEVICES,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSORS,
    CONF_SERIAL,
    CONF_SWITCHES,
    CONF_TEMP_STEP,
    DOMAIN,
    SENSOR_TYPES,
    STATE_CONNECTED,
    STATE_CONNECTION_VERIFIED,
    STATE_ERROR_AUTH,
    STATE_INIT,
    SWITCH_TYPES,
    short,
    url,
)

_LOGGER = logging.getLogger(__name__)

CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL): cv.string,
        vol.Required(CONF_ACCESSKEY): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_NAME, default="Nefit"): cv.string,
        vol.Optional(CONF_SENSORS, default=list(SENSOR_TYPES)): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
        vol.Optional(CONF_SWITCHES, default=list(SWITCH_TYPES)): vol.All(
            cv.ensure_list, [vol.In(SWITCH_TYPES)]
        ),
        vol.Optional(CONF_MIN_TEMP, default=10): cv.positive_int,
        vol.Optional(CONF_MAX_TEMP, default=28): cv.positive_int,
        vol.Optional(CONF_TEMP_STEP, default=0.5): cv.small_float,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_DEVICES): vol.All(
                    cv.ensure_list, [CONNECTION_SCHEMA]
                ),  # array of serial, accesskey, password
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

DOMAINS = ["climate", "sensor", "switch"]


async def async_setup(hass, config):
    """Set up the nefiteasy component."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    if CONF_DEVICES not in conf:
        return True

    for device_conf in conf[CONF_DEVICES]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=device_conf,
            )
        )

    return True


async def async_setup_entry(hass, entry: config_entries.ConfigEntry):
    """Set up the nefiteasy component."""
    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {}

    credentials = dict(entry.data)
    client = NefitEasy(hass, credentials)

    await client.connect()
    _LOGGER.debug("Is connected state? %s", client.connected_state)

    if client.connected_state == STATE_CONNECTION_VERIFIED:
        hass.data[DOMAIN][entry.entry_id]["client"] = client
        _LOGGER.info(
            "Successfully connected %s to Nefit device!",
            credentials.get(CONF_SERIAL),
        )
    else:
        raise ConfigEntryNotReady

    await client.async_refresh()

    for domain in DOMAINS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, domain)
        )

    return True


async def async_unload_entry(hass, entry: config_entries.ConfigEntry):
    """Unload nefit easy component."""
    if not all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in DOMAINS
            ]
        )
    ):
        return False

    client = hass.data[DOMAIN][entry.entry_id]["client"]

    await client.shutdown("Unload entry")

    hass.data[DOMAIN].pop(entry.entry_id)

    return True


class NefitEasy(DataUpdateCoordinator):
    """Supporting class for nefit easy."""

    def __init__(self, hass, config):
        """Initialize nefit easy component."""
        _LOGGER.debug("Initialize Nefit class")

        self._data = {}  # stores device states and values
        self._event = asyncio.Event()
        self._lock = asyncio.Lock()
        self.hass = hass
        self.connected_state = STATE_INIT
        self.expected_end = False
        self.is_connecting = False
        self.serial = config[CONF_SERIAL]
        self._config = config
        self._request = None

        self.nefit = NefitCore(
            serial_number=config[CONF_SERIAL],
            access_key=config[CONF_ACCESSKEY],
            password=config[CONF_PASSWORD],
            message_callback=self.parse_message,
        )

        self.nefit.failed_auth_handler = self.failed_auth_handler
        self.nefit.no_content_callback = self.no_content_callback
        self.nefit.session_end_callback = self.session_end_callback

        self._urls = {}
        self._status_keys = {}

        update_interval = timedelta(seconds=60)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def add_key(self, key, typeconf):
        """Add key to list of endpoints."""
        async with self._lock:
            if url in typeconf:
                self._urls[typeconf[url]] = {"key": key, short: typeconf.get(short)}
            elif short in typeconf:
                self._status_keys[typeconf[short]] = key

    async def connect(self):
        """Connect to nefit easy."""
        _LOGGER.debug("Starting connecting..")
        if not self.is_connecting:
            self.is_connecting = True
            retries_connection = 0

            while self.connected_state != STATE_CONNECTED and retries_connection < 3:
                await self.nefit.connect()
                _LOGGER.debug("Waiting for connected event")
                try:
                    await asyncio.wait_for(
                        self.nefit.xmppclient.connected_event.wait(), timeout=29.0
                    )
                    self.connected_state = STATE_CONNECTED
                    _LOGGER.debug("adding stop listener")
                    self.hass.bus.async_listen_once(
                        EVENT_HOMEASSISTANT_STOP, self.shutdown
                    )
                except asyncio.TimeoutError:
                    _LOGGER.debug(
                        "TimeoutError on waiting for connected event (connection retries=%d)",
                        retries_connection,
                    )
                    retries_connection = retries_connection + 1
                except:  # noqa: E722 pylint: disable=bare-except
                    _LOGGER.debug("Unknown error")

            # test password for decrypting messages if connected
            if self.connected_state == STATE_CONNECTED:
                _LOGGER.info(
                    "Testing connection (connect retries=%d)", retries_connection
                )
                retries_validation = 0
                while (
                    self.connected_state != STATE_CONNECTION_VERIFIED
                    and retries_validation < 3
                ):
                    try:
                        self.nefit.get("/gateway/brandID")
                        await asyncio.wait_for(
                            self.nefit.xmppclient.message_event.wait(), timeout=29.0
                        )
                        self.nefit.xmppclient.message_event.clear()

                        if self.connected_state == STATE_ERROR_AUTH:
                            self.is_connecting = False
                            return

                        self.connected_state = STATE_CONNECTION_VERIFIED
                        _LOGGER.info(
                            "Connected %s with %d retries and %d test retries.",
                            self.serial,
                            retries_connection,
                            retries_validation,
                        )
                    except asyncio.TimeoutError:
                        _LOGGER.error(
                            "Did not get a response in time for testing connection (validation retries=%d).",
                            retries_validation,
                        )
                        retries_validation = retries_validation + 1
                    except:  # noqa: E722 pylint: disable=bare-except
                        _LOGGER.error("No connection while testing connection.")
                        break

            if self.connected_state != STATE_CONNECTION_VERIFIED:
                self.hass.components.persistent_notification.create(
                    f"Did not succeed in connecting {self.serial} to Bosch cloud after retrying 3 times. Retry in 30 seconds.",
                    title="Nefit connect error",
                    notification_id="nefit_connect_error",
                )
                self.is_connecting = False

                # wait 30 seconds to retry
                await asyncio.sleep(30)
                await self.connect()

            self.is_connecting = False
        else:
            _LOGGER.debug("Connection procedure was already running..")

    async def shutdown(self, event):
        """Shutdown."""
        _LOGGER.debug("Shutdown connection to Bosch cloud")
        self.expected_end = True
        await self.nefit.disconnect()

    async def no_content_callback(self, data):
        """Log no content."""
        _LOGGER.debug("no_content_callback: %s", data)

    async def failed_auth_handler(self, event):
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

    async def session_end_callback(self):
        """If connection is closed unexpectedly, try to reconnect."""
        if not self.expected_end:
            self.hass.components.persistent_notification.create(
                f"Unexpected disconnect of {self.serial} with Bosch server. Try to reconnect..",
                title="Nefit disconnect",
                notification_id="nefit_disconnect",
            )

            _LOGGER.info("Starting reconnect procedure.")
            # Reset values
            self.connected_state = STATE_INIT
            self.expected_end = False

            # Retry connection
            await self.connect()

    async def parse_message(self, data):
        """Message received callback function for the XMPP client."""
        if (
            data["id"] == "/ecus/rrc/uiStatus"
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

    async def _async_update_data(self):
        """Update data via library."""
        if self.connected_state != STATE_CONNECTION_VERIFIED:
            raise UpdateFailed("Nefit easy not connected!")

        async with self._lock:
            url = "/ecus/rrc/uiStatus"
            await self._async_get_url(url)

            for url in self._urls:
                await self._async_get_url(url)

        return self._data

    async def async_init_presence(self, endpoint, index):
        """Init presence detection."""
        async with self._lock:
            url = f"{endpoint}/userprofile{index}/active"
            await self._async_get_url(url)

            if self._data[f"presence{index}_active"] == "on":
                url = f"{endpoint}/userprofile{index}/name"
                await self._async_get_url(url)

                return self._data.get(f"presence{index}_name")

            return None

    async def update_ui_status_later(self, delay):
        """Force update of uiStatus after delay."""
        self.hass.loop.call_later(delay, self.nefit.get, "/ecus/rrc/uiStatus")

    async def _async_get_url(self, url):
        self._event.clear()
        self._request = url
        self.nefit.get(url)
        await asyncio.wait_for(self._event.wait(), timeout=9)
        self._request = None
