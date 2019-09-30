"""
Support for first generation Bosch smart home thermostats: Nefit Easy, Junkers CT100 etc
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xxxxxx/
"""

REQUIREMENTS = ['aionefit==0.4']

import logging
import concurrent
import asyncio
import voluptuous as vol

#from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import PlatformNotReady, InvalidStateError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.entity import Entity


_LOGGER = logging.getLogger(__name__)

DOMAIN = "nefiteasy"

CONF_SERIAL = "serial"
CONF_ACCESSKEY = "accesskey"
CONF_PASSWORD = "password"
CONF_NAME = "name"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_SERIAL): cv.string,
                vol.Required(CONF_ACCESSKEY): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_NAME, default="Nefit Easy"): cv.string,
                vol.Optional(CONF_MIN_TEMP, default=10): cv.positive_int,
                vol.Optional(CONF_MAX_TEMP, default=28): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

DISPATCHER_ON_DEVICE_UPDATE = "nefiteasy_{key}_on_device_update"

STATE_CONNECTED = 'connected'
STATE_INIT = 'initializing'
STATE_ERROR_AUTH = 'authentication_failed'


async def async_setup(hass, config):

    nefit_data = hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["config"] = config[DOMAIN]

    credentials = dict(config[DOMAIN])

    client = nefit_data["client"] = NefitEasy(hass, credentials)
    await client.connect()

    for platform in ["climate", "sensor", "switch"]: #["climate", "sensor", "switch"]:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    return True


class NefitEasy:
    def __init__(self, hass, credentials):
        from aionefit import NefitCore
        _LOGGER.debug("Initialize Nefit class")

        self.data = {}
        self.keys = {} #unique name for entity
        self.events = {}
        self.hass = hass
        self.connected_state = STATE_INIT
        
        self.nefit = NefitCore(serial_number=credentials.get(CONF_SERIAL),
                       access_key=credentials.get(CONF_ACCESSKEY),
                       password=credentials.get(CONF_PASSWORD),
                       message_callback=self.parse_message)
        
        self.nefit.failed_auth_handler = self.failed_auth_handler
        self.nefit.no_content_callback = self.no_content_callback

    async def connect(self):
        self.nefit.connect()
        _LOGGER.debug("Waiting for connected event")        
        try:
            # await self.nefit.xmppclient.connected_event.wait()
            await asyncio.wait_for(self.nefit.xmppclient.connected_event.wait(), timeout=60.0)
            self.connected_state = STATE_CONNECTED
            _LOGGER.debug("adding stop listener")
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,
                                            self.shutdown)
        except concurrent.futures._base.TimeoutError:
            _LOGGER.debug("TimeoutError on waiting for connected event")
            self.hass.components.persistent_notification.create( 
                'Timeout while connecting to Bosch cloud.',
                title='Nefit error',
                notification_id='nefit_logon_error')
            raise PlatformNotReady
        
        if self.connected_state == STATE_ERROR_AUTH:
            self.hass.components.persistent_notification.create( 
                'Invalid credentials while connecting to Bosch cloud.',
                title='Nefit error',
                notification_id='nefit_logon_error')
            raise PlatformNotReady

    def shutdown(self, event):
        _LOGGER.debug("Shutdown connection to Bosch cloud")
        self.nefit.disconnect()

    def no_content_callback(self, data):
        _LOGGER.debug("no_content_callback: %s", data)

    def failed_auth_handler(self, event):
        self.connected_state = STATE_ERROR_AUTH
        self.nefit.xmppclient.connected_event.set()

    def parse_message(self, data):
        """Message received callback function for the XMPP client.
        """
        _LOGGER.debug("parse_message callback called with data %s", data)
        if not 'id' in data:
            _LOGGER.error("Unknown response received: %s", data)
            return

        if data['id'] in self.keys:
            key = self.keys[data['id']]
            _LOGGER.debug("Got update for %s.", key)

            if data['id'] == '/ecus/rrc/uiStatus':
                self.data['temp_setpoint'] = float(data['value']['TSP']) #for climate
                self.data['inhouse_temperature'] = float(data['value']['IHT'])  #for climate
                self.data['user_mode'] = data['value']['UMD']  #for climate
                self.data['boiler_indicator'] = data['value']['BAI']  #for climate
                self.data['last_update'] = data['value']['CTD']

            self.data[key] = data['value']

            #send update signal to dispatcher to pick up new state
            signal = DISPATCHER_ON_DEVICE_UPDATE.format(key=key)
            async_dispatcher_send(self.hass, signal)

            # Mark event as finished
            if key in self.events:
                self.events[key].set()


class NefitDevice(Entity):
    """Representation of a Nefit device."""

    def __init__(self, client, device):
        """Initialize the sensor."""
        self._client = client
        self._device = device
        self._key = device['key']
        self._url = device['url']
        client.events[self._key] = asyncio.Event()
        client.keys[self._url] = self._key

        self._remove_callbacks: List[Callable[[], None]] = []

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added."""
        kwargs = {
            "key": self._key,
        }
        self._remove_callbacks.append(
            async_dispatcher_connect(
                self.hass, DISPATCHER_ON_DEVICE_UPDATE.format(**kwargs), self.async_schedule_update_ha_state
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks."""
        for remove_callback in self._remove_callbacks:
            remove_callback()
        self._remove_callbacks = []

    async def async_update(self):
        """Request latest data."""
        _LOGGER.debug("async_update called for %s", self._key)
        event = self._client.events[self._key]
        event.clear() #clear old event
        self._client.nefit.get(self.get_endpoint())
        try:
            await asyncio.wait_for(event.wait(), timeout=10)
        except concurrent.futures._base.TimeoutError:
            _LOGGER.debug("Did not get an update in time for %s.", self._key)
            event.clear() #clear event
        
    @property
    def name(self):
        """Return the name of the device. """
        return self._device['name']

    def get_endpoint(self):
        """Return the API endpoint."""
        return self._device['url']

    @property
    def should_poll(self) -> bool:
        """Enable polling for regular state updates"""
        return True