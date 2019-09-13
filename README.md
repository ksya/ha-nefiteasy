# ha-nefiteasy
Nefit Easy connection for Home Assistant

Big thanks to marconfus for the aionefit library and his work on the ha-nefit-ng compontent! 
* https://github.com/marconfus/aionefit
* https://github.com/marconfus/ha-nefit-ng

## Installation

Create ```custom_components/nefiteasy/``` in your homeassistant config directory and copy the files of this repository into this directory.
Restart Home Assistant or Hass.io.

## Configuration

```
nefiteasy:
  serial: 'XXXXXXXXX'
  accesskey: 'xxxxxxxxx'
  password: 'xxxxxxxxx'
  name: Nefit Easy #optional
  min_temp: 15 #optional
  max_temp: 27 #optional
```

If any of your secrets in the configuration is numbers only, make sure to put it between quotes (`'`) to have homeassistant parse them correctly.

## Debugging problems

```
logger:
  default: info
  logs:
    custom_components.nefiteasy: debug
    aionefit: debug
```
