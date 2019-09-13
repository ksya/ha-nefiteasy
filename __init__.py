"""
Support for first generation Bosch smart home thermostats: Nefit Easy, Junkers CT100 etc
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xxxxxx/
"""

REQUIREMENTS = ['aionefit==0.3']

import logging
import concurrent
import asyncio
import voluptuous as vol

#from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import PlatformNotReady, InvalidStateError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

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
                vol.Optional(CONF_MAX_TEMP, default=35): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)



async def async_setup(hass, config):

    nefit_data = hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["config"] = config[DOMAIN]

    credentials = dict(config[DOMAIN])

    client = nefit_data["client"] = NefitEasy(hass, credentials)
    await client.connect()

    for platform in ["climate", "sensor", "switch"]:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    return True


class NefitEasy:
    def __init__(self, hass, credentials):
        from aionefit import NefitCore
        _LOGGER.debug("Initialize Nefit class")

        self.data = {}
        self.ids = {}
        self.hass = hass
        self.error_state = "initializing"
        self.events = { '/ecus/rrc/uiStatus': asyncio.Event() }
        
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
            await asyncio.wait_for(self.nefit.xmppclient.connected_event.wait(), timeout=15.0)
            _LOGGER.debug("adding stop listener")
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,
                                            self.shutdown)
        except concurrent.futures._base.TimeoutError:
            _LOGGER.debug("TimeoutError on waiting for connected event")
            self.hass.components.persistent_notification.create( 
                'Timeout while connecting to Bosch cloud. Retrying in the background',
                title='Nefit error',
                notification_id='nefit_logon_error')
            raise PlatformNotReady
        
        if self.error_state == "authentication_failed":
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
        self.error_state = "authentication_failed"
        self.nefit.xmppclient.connected_event.set()

    def parse_message(self, data):
        """Message received callback function for the XMPP client.
        """
        _LOGGER.debug("parse_message callback called with data %s", data)
        if not 'id' in data:
            _LOGGER.error("Unknown response received: %s", data)
            return

        if data['id'] == '/ecus/rrc/uiStatus':
            self.data['uistatus'] = data['value']
            self.data['temp_setpoint'] = float(data['value']['TSP']) #for climate
            self.data['inhouse_temperature'] = float(data['value']['IHT'])  #for climate
            self.data['user_mode'] = data['value']['UMD']  #for climate
            self.data['boiler_indicator'] = data['value']['BAI']  #for climate
            self.data['last_update'] = data['value']['CTD']

        elif data['id'] == '/dhwCircuits/dhwA/dhwOperationClockMode' or data['id'] == '/dhwCircuits/dhwA/dhwOperationManualMode':
            self.data['hot_water'] = data['value']
            self.events['hot_water'].set()

        if data['id'] in self.events:
            if data['id'] in self.ids:
                self.data[self.ids[data['id']]] = data['value']

            # Mark event as finished
            self.events[data['id']].set()