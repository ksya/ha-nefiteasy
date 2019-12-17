"""
Support for first generation Bosch smart home thermostats: Nefit Easy, Junkers CT100 etc
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xxxxxx/
"""

import logging
import concurrent
import asyncio
import voluptuous as vol

#from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (DOMAIN, CONF_DEVICES,
    CONF_SERIAL, CONF_ACCESSKEY, CONF_PASSWORD, CONF_NAME,
    CONF_MIN_TEMP, CONF_MAX_TEMP, CONF_SWITCHES, CONF_SENSORS, 
    DISPATCHER_ON_DEVICE_UPDATE, 
    STATE_CONNECTED, STATE_INIT, STATE_ERROR_AUTH, 
    SENSOR_TYPES, SWITCH_TYPES)

_LOGGER = logging.getLogger(__name__)

CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL): cv.string,
        vol.Required(CONF_ACCESSKEY): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_NAME, default="Nefit"): cv.string,
        vol.Optional(CONF_SENSORS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
        vol.Optional(CONF_SWITCHES, default=list(SWITCH_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SWITCH_TYPES)]),
        vol.Optional(CONF_MIN_TEMP, default=10): cv.positive_int,
        vol.Optional(CONF_MAX_TEMP, default=28): cv.positive_int,
    })

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [CONNECTION_SCHEMA]), # array of serial, accesskey, password
    })
}, extra=vol.ALLOW_EXTRA)



async def async_setup(hass, config):

    nefit_data = hass.data[DOMAIN] = {}
    nefit_data['devices'] = []

    conf = config.get(DOMAIN)

    if CONF_DEVICES not in conf:
        return True

    for device_conf in conf[CONF_DEVICES]:
        credentials = dict(device_conf)
        nefit_data['devices'].append({})
        device = nefit_data['devices'][-1]
        device['client'] = client = NefitEasy(hass, credentials)
        device['config'] = device_conf

        await client.connect()

    for platform in ["climate", "sensor", "switch"]:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, device_conf)
        )

    return True


class NefitEasy:
    def __init__(self, hass, credentials):
        from aionefit import NefitCore
        _LOGGER.debug("Initialize Nefit class")

        self.data = {} #stores device states and values
        self.keys = {} #unique name for entity
        self.events = {}
        self.uiStatusVars = {} #variables to monitor for sensors
        self.hass = hass
        self.connected_state = STATE_INIT
        self.expected_end = False

        self.nefit = NefitCore(serial_number=credentials.get(CONF_SERIAL),
                       access_key=credentials.get(CONF_ACCESSKEY),
                       password=credentials.get(CONF_PASSWORD),
                       message_callback=self.parse_message)
        
        self.nefit.failed_auth_handler = self.failed_auth_handler
        self.nefit.no_content_callback = self.no_content_callback
        self.nefit.session_end_callback = self.session_end_callback

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
        self.expected_end = True
        self.nefit.disconnect()

    def no_content_callback(self, data):
        _LOGGER.debug("no_content_callback: %s", data)

    def failed_auth_handler(self, event):
        self.connected_state = STATE_ERROR_AUTH
        self.nefit.xmppclient.connected_event.set()

    def session_end_callback(self):
        """If connection is closed unexpectedly, try to reconnect"""
        if not self.expected_end:
            self.hass.components.persistent_notification.create( 
                'Unexpected disconnect with Bosch server',
                title='Nefit error',
                notification_id='nefit_disconnect')
            self.connect()

    def parse_message(self, data):
        """Message received callback function for the XMPP client.
        """
        _LOGGER.debug("parse_message data %s", data)
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

                for uikey in self.uiStatusVars:
                    self.updateDeviceValue(uikey, data['value'].get(self.uiStatusVars[uikey]))

            self.updateDeviceValue(key, data['value'])

            # Mark event as finished if it was part of an update action
            if key in self.events:
                self.events[key].set()

    def updateDeviceValue(self, key, value):
        """Store new device value and send to dispatcher to be picked up by device"""
        self.data[key] = value

        #send update signal to dispatcher to pick up new state
        signal = DISPATCHER_ON_DEVICE_UPDATE.format(key=key)
        async_dispatcher_send(self.hass, signal)

    async def get_value(self, key, url):
        isNewKey = not url in self.keys
        if isNewKey:
            self.events[key] = asyncio.Event()
            self.keys[url] = key
        event = self.events[key]
        event.clear() #clear old event
        self.nefit.get(url)
        await asyncio.wait_for(event.wait(), timeout=9)
        if isNewKey:
            del self.events[key]
            del self.keys[url]
        return self.data[key]