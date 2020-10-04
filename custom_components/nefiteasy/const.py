"""Constants for the nefiteasy component."""

from homeassistant.const import (TEMP_CELSIUS, PRESSURE_BAR)

DOMAIN = 'nefiteasy'

CONF_DEVICES = 'devices'
CONF_SERIAL = 'serial'
CONF_ACCESSKEY = 'accesskey'
CONF_PASSWORD = 'password'
CONF_NAME = 'name'
CONF_MIN_TEMP = 'min_temp'
CONF_MAX_TEMP = 'max_temp'
CONF_TEMP_STEP = 'temp_step'
CONF_SWITCHES = 'switches'
CONF_SENSORS = 'sensors'

DISPATCHER_ON_DEVICE_UPDATE = "nefiteasy_{key}_on_device_update"

STATE_CONNECTED = 'connected'
STATE_CONNECTION_VERIFIED = 'connection_verified'
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
        name: "Year total",
        url: '/ecus/rrc/recordings/yearTotal',
        unit: 'm3',
        icon: 'mdi:gas-cylinder'
    },
    'status': {
        name: "status",
        url: '/system/appliance/displaycode'
    },
    'supply_temperature': {
        name: "Supply temperature",
        url: '/heatingCircuits/hc1/actualSupplyTemperature',
        unit: TEMP_CELSIUS,
        device_class: 'temperature'
    },
    'outdoor_temperature': {
        name: "Outdoor temperature",
        url: '/system/sensors/temperatures/outdoor_t1',
        unit: TEMP_CELSIUS,
        device_class: 'temperature'
    },
    'system_pressure': {
        name: "System pressure",
        url: '/system/appliance/systemPressure',
        unit: PRESSURE_BAR,
        device_class: 'pressure'
    },
    'active_program': {
        name: "Active program",
        url: '/ecus/rrc/userprogram/activeprogram',
        icon: 'mdi:calendar-today'
    },
    'hot_water_operation': {
        name: "Hot water operation",
        url: '/dhwCircuits/dhwA/dhwOperationType'
    },
}


SWITCH_TYPES = {
    'hot_water': {
        name: "Hot water",
        short: 'DHW',
        icon: 'mdi:water-boiler'
    },
    'holiday_mode': {
        name: "Holiday mode",
        url: '/heatingCircuits/hc1/holidayMode/status',
        short: 'HMD',
        icon: 'mdi:briefcase-outline'
    },
    'fireplace_mode': {
        name: "Fireplace mode",
        url: '/ecus/rrc/userprogram/fireplacefunction',
        short: 'FPA',
        icon: 'mdi:fire'
    },
    'today_as_sunday': {
        name: "Today as Sunday",
        url: '/ecus/rrc/dayassunday/day10/active',
        short: 'DAS',
        icon: 'mdi:calendar-star'
    },
    'tomorrow_as_sunday': {
        name: "Tomorrow as Sunday",
        url: '/ecus/rrc/dayassunday/day11/active',
        short: 'TAS',
        icon: 'mdi:calendar-star'
    },
    'preheating': {
        name: "Preheating",
        url: '/ecus/rrc/userprogram/preheating',
        icon: 'mdi:calendar-clock'
    },
    'home_entrance_detection': {
        name: "Presence {}",
        icon: 'mdi:account-check'
    },
    'weather_dependent': {
        name: "Weather dependent",
        url: '/heatingCircuits/hc1/control',
        icon: 'mdi:weather-partly-snowy-rainy'
    },
    'lockui': {
        name: "Lock UI",
        url: '/ecus/rrc/lockuserinterface',
        icon: 'mdi:lock'
    }
}