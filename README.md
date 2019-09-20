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

## FAQ
#### HS cannot connect to Bosch cloud 

If you experience errors during the boot of HA regarding the connection to the Bosch cloud ie ```Timeout while connecting to Bosch cloud. Retrying in the background```, you may want to change the OpenSSL configuration.
The OpenSSL defaults for Buster are causing the problem, probably because Nefit/Bosch is using either an outdated TLS version or an outdated cipher.

Edit ```/etc/ssl/openssl.cnf``` and change the system wide defaults back to their previous values(pre-Buster):
```
MinProtocol = None
CipherString = DEFAULT
```

https://www.debian.org/releases/stable/amd64/release-notes/ch-information.en.html#openssl-defaults
