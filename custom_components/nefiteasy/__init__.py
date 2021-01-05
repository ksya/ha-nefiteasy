"""Support for first generation Bosch smart home thermostats: Nefit Easy, Junkers CT100 etc."""

import asyncio
import logging

from aionefit import NefitCore
import voluptuous as vol

from homeassistant import config_entries

# from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

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
    DISPATCHER_ON_DEVICE_UPDATE,
    DOMAIN,
    SENSOR_TYPES,
    STATE_CONNECTED,
    STATE_CONNECTION_VERIFIED,
    STATE_ERROR_AUTH,
    STATE_INIT,
    SWITCH_TYPES,
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


class NefitEasy:
    """Supporting class for nefit easy."""

    def __init__(self, hass, credentials):
        """Initialize nefit easy component."""
        _LOGGER.debug("Initialize Nefit class")

        self.data = {}  # stores device states and values
        self.keys = {}  # unique name for entity
        self.events = {}
        self.ui_status_vars = {}  # variables to monitor for sensors
        self.hass = hass
        self.connected_state = STATE_INIT
        self.expected_end = False
        self.is_connecting = False
        self.serial = credentials.get(CONF_SERIAL)

        self.nefit = NefitCore(
            serial_number=credentials.get(CONF_SERIAL),
            access_key=credentials.get(CONF_ACCESSKEY),
            password=credentials.get(CONF_PASSWORD),
            message_callback=self.parse_message,
        )

        self.nefit.failed_auth_handler = self.failed_auth_handler
        self.nefit.no_content_callback = self.no_content_callback
        self.nefit.session_end_callback = self.session_end_callback

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
        _LOGGER.debug("parse_message data %s", data)
        if "id" not in data:
            _LOGGER.error("Unknown response received: %s", data)
            return

        if data["id"] in self.keys:
            key = self.keys[data["id"]]
            _LOGGER.debug("Got update for %s.", key)

            if (
                data["id"] == "/ecus/rrc/uiStatus"
                and self.connected_state == STATE_CONNECTION_VERIFIED
            ):
                self.data["temp_setpoint"] = float(data["value"]["TSP"])  # for climate
                self.data["inhouse_temperature"] = float(
                    data["value"]["IHT"]
                )  # for climate
                self.data["user_mode"] = data["value"]["UMD"]  # for climate
                self.data["boiler_indicator"] = data["value"]["BAI"]  # for climate
                self.data["last_update"] = data["value"]["CTD"]

                # Update all sensors/switches when there is new data form uiStatus
                for uikey in self.ui_status_vars:
                    self.update_device_value(
                        uikey, data["value"].get(self.ui_status_vars[uikey])
                    )

            self.update_device_value(key, data["value"])

            # Mark event as finished if it was part of an update action
            if key in self.events:
                self.events[key].set()

    def update_device_value(self, key, value):
        """Store new device value and send to dispatcher to be picked up by device."""
        self.data[key] = value

        # send update signal to dispatcher to pick up new state
        signal = DISPATCHER_ON_DEVICE_UPDATE.format(key=key)
        async_dispatcher_send(self.hass, signal)

    async def get_value(self, key, url):
        """Get value."""
        is_new_key = url not in self.keys
        if is_new_key:
            self.events[key] = asyncio.Event()
            self.keys[url] = key
        event = self.events[key]
        event.clear()  # clear old event
        self.nefit.get(url)
        await asyncio.wait_for(event.wait(), timeout=9)
        if is_new_key:
            del self.events[key]
            del self.keys[url]
        return self.data[key]
