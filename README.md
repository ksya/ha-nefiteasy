# ha-nefiteasy
Nefit Easy connection for Home Assistant

![Build](https://github.com/ksya/ha-nefiteasy/actions/workflows/push.yml/badge.svg)

Big thanks to marconfus for the aionefit library and his work on the ha-nefit-ng component! 
* https://github.com/marconfus/aionefit
* https://github.com/marconfus/ha-nefit-ng

## Installation

1. Copy the folder ```custom_components/nefiteasy/``` to your homeassistant config directory.
2. Restart Home Assistant.

## Alternative install using HACS
1. Add "https://github.com/ksya/ha-nefiteasy" to your custom repositories in the Settings tab of HACS. 
2. Choose "Integration".
3. Press the "save" button.
4. Go to the integrations tab and search for Nefit Easy.
5. Click and install from there.

## Configuration
All configuration can be done from within Home Assistant:
1. Go to Settings
2. Go to Integrations
3. At the bottom right, click Add Integration
4. Search for "Nefit" -> Nefit Easy Bosch Thermostat
5. Fill in your serial number, access key and password
6. Save

> Make sure to enter serial number and access key without spaces!

### Limit sensors and switches
Some entities are disabled by default, if needed they can be enabled. Entities that are disabled will not be updated.

## Available sensors & switches
### Sensors
```
- year_total
- status
- supply_temperature
- outdoor_temperature
- system_pressure
- active_program
- hot_water_operation
- inhouse_temperature
- target_temperature
```

### Controls
```
- hot_water
- holiday_mode
- fireplace_mode
- today_as_sunday
- tomorrow_as_sunday
- preheating
- home_entrance_detection
- weather_dependent
- lockui
- active_program
- shower_timer
- shower_timer_duration
```

## Debugging problems
Turn on debug for both aionefit as custom_components.nefiteasy:
```
logger:
  default: info
  logs:
    custom_components.nefiteasy: debug
    aionefit: debug
```

## FAQ
#### HA cannot connect to Bosch cloud 

If you experience errors during the boot of HA regarding the connection to the Bosch cloud ie ```Timeout while connecting to Bosch cloud. Retrying in the background```, you may want to change the OpenSSL configuration.
The OpenSSL defaults for Buster are causing the problem, probably because Nefit/Bosch is using either an outdated TLS version or an outdated cipher.

Edit ```/etc/ssl/openssl.cnf``` and change the system wide defaults back to their previous values(pre-Buster):
```
MinProtocol = None
CipherString = DEFAULT
```

https://www.debian.org/releases/stable/amd64/release-notes/ch-information.en.html#openssl-defaults
