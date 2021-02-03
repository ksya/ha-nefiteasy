Home Assistant Custom Component for Bosch Nefit Easy thermostat

## Configuration
All configuration can be done from within Home Assistant:
1. Go to Settings
2. Go to Integrations
3. At the bottom right, click Add Integration
4. Search for "Nefit" -> Nefit Easy Bosch Thermostat
5. Fill in your serial number, access key and password
6. Save


### Limit sensors and switches
Just disable the enitities from UI you dont want. Those will not be updated anymore.

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
```

### Switches
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
