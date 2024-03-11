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

## Controls/Switches & Sensors

### Controls/Switches

> None enabled by default.

| Key | Name | Description |
| - | - | -  |
| active_program | Active program | Clock [program] 1 or 2 |
| fireplace_mode | Fireplace mode | Other rooms stay warm as the fire burns |
| holiday_mode | Holiday mode | Define settings in the app. Activate/Deactivate them in Home Assistant |
| hot_water | Hot water | Hot water preheat |
| home_entrance_detection | Presence | "The Nefit Easy detects the presence of the smart device in the home and adjusts the room temperature accordingly.<br><br>To let this function, operate mobile Internet and Wi-Fi must be enabled continuously. Location services must be enabled in the settings; optionally you can use the location modus -> battery saving if your device supports it." |
| lockui | Lock UI | "Manual operation of the thermostat can be locked to prevent unintended adjustments." |
| preheating | Preheating | |
| shower_timer | Shower timer | "Shortening the duration of showering helps save energy.<br><br>3 minutes prior to the allotted time set cold water will come out of the hot water tap temporarily. When the allotted tome has fully passed, cold water will come out of the hot water tap until the tap is closed." |
| shower_timer_duration | Shower timer duration | Set time for the 'Shower timer' in minutes. |
| today_as_sunday | Today as Sunday | |
| tomorrow_as_sunday | Tomorrow as Sunday
| weather_dependent | Weather dependent | "Weather compensation control based on the local outdoor temperature.<br><br> Weather compensation control is best used with thermostatic radiator valves or thermostatically controlled radiant heating.<br><br>Please note:<br>The control is not based on the measured room temperature. Weather compensation control is comfort enhancing, but may result in increased heating costs. This control requires knowledge of weather compensation control. Ask your installer for support." |
| temperature_adjustment | Temperature Adjustment | Calibrate the measured temperature between +2 and -2 °C. |

### Sensors

| Key | Name | UoM | Description | Enabled by default |
| - | - | :-: | - | :-: |
| actual_power | Power | | | &#x2714; |
| hot_water_operation | Hot water operation |  | "When 'Follow program' is off, preheat function will be active or your indirect storage tank will remain heated.<br><br>Follow heating program: Hot water will be heated inline with heating 'Wakeup' & 'Home' activities, but extended one hour before and after these periods.<br><br>Custom program: Use this to set an independent hot water clock program.<br><br>For combi boilers: To disable preheat permanently, please refer to the boiler user manual." | &#x274C; |
| inhouse_temperature | Inhouse temperature | °C | Current room temperature | &#x274C; |
| outdoor_temperature | Outdoor temperature | °C | Outdoor temperature | &#x2714; |
| status | status | | Status of the boiler | &#x2714; |
| supply_temperature | Supply temperature | °C | Temperature of (hot) water ready to supply | &#x2714; |
| system_pressure | System pressure | Bar | System water pressure | &#x2714; |
| target_temperature | Target temperature | °C | Target temperature | &#x274C; |
| year_total | Year total | m<sup>3</sup> | Volume of gas consumed since Jan 1<sup>st</sup> | &#x2714; |

#### Sensor values

##### Status

| Code | Description |
| :-: | - |
| -H | central heating active |
| =H | hot water active |
| 0C<br>0L<br>0U | system starting |
| 0E | system waiting |
| 0H | system standby |
| 0A<br>0Y | system waiting (boiler cannot transfer heat to central heating) |
| 2E<br>H07 | boiler water pressure too low |
| 2F<br>2L<br>2P<br>2U<br>4F<br>4L | sensors measured abnormal temperature |
| 6A<br>6C | burner doesn't ignite |
| rE | system restarting |


##### Hot water operation
```
- follow-ch
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
