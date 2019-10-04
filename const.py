"""Constants for the nefiteasy component."""

from homeassistant.const import (TEMP_CELSIUS, PRESSURE_BAR)

DOMAIN = 'nefiteasy'

CONF_SERIAL = 'serial'
CONF_ACCESSKEY = 'accesskey'
CONF_PASSWORD = 'password'
CONF_NAME = 'name'
CONF_MIN_TEMP = 'min_temp'
CONF_MAX_TEMP = 'max_temp'
CONF_SWITCHES = 'switches'
CONF_SENSORS = 'sensors'

DISPATCHER_ON_DEVICE_UPDATE = "nefiteasy_{key}_on_device_update"

STATE_CONNECTED = 'connected'
STATE_INIT = 'initializing'
STATE_ERROR_AUTH = 'authentication_failed'

name = 'name'
url = 'url'
unit = 'unit'
device_class = 'device_class'
short = 'short'
icon = 'icon'

SENSOR_TYPES = {
    'year_total': {
        name: "Nefit Year total",
        url: '/ecus/rrc/recordings/yearTotal',
        unit: 'm3'
    },
    'status': {
        name: "Nefit status",
        url: '/system/appliance/displaycode'
    },
    'supply_temperature': {
        name: "Nefit Supply temperature",
        url: '/heatingCircuits/hc1/actualSupplyTemperature',
        unit: TEMP_CELSIUS,
        device_class: 'temperature'
    },
    'outdoor_temperature': {
        name: "Nefit Outdoor temperature",
        url: '/system/sensors/temperatures/outdoor_t1',
        unit: TEMP_CELSIUS,
        device_class: 'temperature'
    },
    'system_pressure': {
        name: "Nefit CV pressure",
        url: '/system/appliance/systemPressure',
        unit: PRESSURE_BAR,
        device_class: 'pressure'
    },
    'active_program': {
        name: "Nefit Active program",
        url: '/ecus/rrc/userprogram/activeprogram'
    },
    'hot_water_operation': {
        name: "Nefit Hot water operation",
        url: '/dhwCircuits/dhwA/dhwOperationType'
    },
}


SWITCH_TYPES = {
    'hot_water': {
        name: "Nefit Hot water",
        short: 'DHW'
    },
    'holiday_mode': {
        name: "Nefit Holiday mode",
        url: '/heatingCircuits/hc1/holidayMode/status',
        short: 'HMD'
    },
    'fireplace_mode': {
        name: "Nefit Fireplace mode",
        url: '/ecus/rrc/userprogram/fireplacefunction',
        short: 'FPA'
    },
    'today_as_sunday': {
        name: "Nefit Today as Sunday",
        url: '/ecus/rrc/dayassunday/day10/active',
        short: 'DAS'
    },
    'tomorrow_as_sunday': {
        name: "Nefit Tomorrow as Sunday",
        url: '/ecus/rrc/dayassunday/day11/active',
        short: 'TAS'
    },
    'preheating': {
        name: "Nefit Preheating",
        url: '/ecus/rrc/userprogram/preheating'
    },
}