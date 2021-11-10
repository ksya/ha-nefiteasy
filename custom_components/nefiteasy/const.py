"""Constants for the nefiteasy component."""
from __future__ import annotations

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
)
from homeassistant.const import (
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    PRESSURE_BAR,
    TEMP_CELSIUS,
    VOLUME_CUBIC_METERS,
)

from .models import (
    NefitNumberEntityDescription,
    NefitSelectEntityDescription,
    NefitSensorEntityDescription,
    NefitSwitchEntityDescription,
)

DOMAIN = "nefiteasy"

CONF_DEVICES = "devices"
CONF_SERIAL = "serial"
CONF_ACCESSKEY = "accesskey"
CONF_PASSWORD = "password"
CONF_NAME = "name"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_TEMP_STEP = "temp_step"
CONF_SWITCHES = "switches"
CONF_SENSORS = "sensors"

STATE_CONNECTED = "connected"
STATE_CONNECTION_VERIFIED = "connection_verified"
STATE_INIT = "initializing"
STATE_ERROR_AUTH = "authentication_failed"

name = "name"
url = "url"
unit = "unit"
device_class = "device_class"
short = "short"
icon = "icon"
options = "options"

SELECTS: tuple[NefitSelectEntityDescription, ...] = (
    NefitSelectEntityDescription(
        key="active_program",
        name="Active program",
        url="/ecus/rrc/userprogram/activeprogram",
        icon="mdi:calendar-today",
        options={
            0: "Clock 1",
            1: "Clock 2",
        },
        entity_registry_enabled_default=False,
    ),
)

SENSORS: tuple[NefitSensorEntityDescription, ...] = (
    NefitSensorEntityDescription(
        key="year_total",
        name="Year total",
        url="/ecus/rrc/recordings/yearTotal",
        unit=VOLUME_CUBIC_METERS,
        device_class=DEVICE_CLASS_GAS,
        state_class=STATE_CLASS_TOTAL_INCREASING,
    ),
    NefitSensorEntityDescription(
        key="status", name="status", url="/system/appliance/displaycode"
    ),
    NefitSensorEntityDescription(
        key="supply_temperature",
        name="Supply temperature",
        url="/heatingCircuits/hc1/actualSupplyTemperature",
        unit=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    NefitSensorEntityDescription(
        key="outdoor_temperature",
        name="Outdoor temperature",
        url="/system/sensors/temperatures/outdoor_t1",
        unit=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    NefitSensorEntityDescription(
        key="system_pressure",
        name="System pressure",
        url="/system/appliance/systemPressure",
        unit=PRESSURE_BAR,
        device_class=DEVICE_CLASS_PRESSURE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    NefitSensorEntityDescription(
        key="hot_water_operation",
        name="Hot water operation",
        url="/dhwCircuits/dhwA/dhwOperationType",
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="inhouse_temperature",
        name="Inhouse temperature",
        short="IHT",
        unit=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
)

SWITCHES: tuple[NefitSwitchEntityDescription, ...] = (
    NefitSwitchEntityDescription(
        key="hot_water",
        name="Hot water",
        short="DHW",
        icon="mdi:water-boiler",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="holiday_mode",
        name="Holiday mode",
        url="/heatingCircuits/hc1/holidayMode/status",
        short="HMD",
        icon="mdi:briefcase-outline",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="fireplace_mode",
        name="Fireplace mode",
        url="/ecus/rrc/userprogram/fireplacefunction",
        short="FPA",
        icon="mdi:fire",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="today_as_sunday",
        name="Today as Sunday",
        url="/ecus/rrc/dayassunday/day10/active",
        short="DAS",
        icon="mdi:calendar-star",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="tomorrow_as_sunday",
        name="Tomorrow as Sunday",
        url="/ecus/rrc/dayassunday/day11/active",
        short="TAS",
        icon="mdi:calendar-star",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="preheating",
        name="Preheating",
        url="/ecus/rrc/userprogram/preheating",
        icon="mdi:calendar-clock",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="home_entrance_detection",
        name="Presence {}",
        icon="mdi:account-check",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="weather_dependent",
        name="Weather dependent",
        url="/heatingCircuits/hc1/control",
        icon="mdi:weather-partly-snowy-rainy",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="lockui",
        name="Lock UI",
        url="/ecus/rrc/lockuserinterface",
        icon="mdi:lock",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="shower_timer",
        name="Shower timer",
        url="/dhwCircuits/dhwA/extraDhw/status",
        icon="mdi:timer-cog-outline",
        entity_registry_enabled_default=False,
    ),
)

NUMBERS: tuple[NefitNumberEntityDescription, ...] = (
    NefitNumberEntityDescription(
        key="shower_timer_duration",
        name="Shower timer duration",
        url="/dhwCircuits/dhwA/extraDhw/duration",
        icon="mdi:timer-outline",
        min_value=0,
        max_value=60,
        step=1,
        entity_registry_enabled_default=False,
    ),
)
