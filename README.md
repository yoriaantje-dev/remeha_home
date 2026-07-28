# Remeha Home integration for Home Assistant

> **This is a fork.** All credit for the original integration goes to
> [@msvisser](https://github.com/msvisser) — see the upstream project at
> [msvisser/remeha_home](https://github.com/msvisser/remeha_home).
> This fork adds domestic hot water (DHW) control as a `water_heater` entity
> (schedule / comfort / **boost** / off, target temperature, and native
> ~30 min boost). See [DHW hot water control](#dhw-hot-water-control) below.

This integration lets you control your Remeha Home thermostats from Home Assistant.

**Before using this integration, make sure you have set up your thermostat in the [Remeha Home](https://play.google.com/store/apps/details?id=com.bdrthermea.application.remeha) app.**
If you are unable to use the Remeha Home app for your thermostat, this integration will not work.

There have been reports by users that this intergration will also work for Baxi, De Dietrich, and Brötje systems (and possibly other BDR Thermea products).
You can simply log in using the credentials that you would use in the respective apps.

## Current features
- All climate zones are exposed as [climate](https://www.home-assistant.io/integrations/climate/) entities with:
    - The following modes:
        - Auto mode: the thermostat will follow the clock program.
        If the target temperature is changed, it will temporarily override the clock program until the next target temperature change in the schedule.
        - Heat mode: the thermostat will be set to manual mode and continuously hold the set temperature.
        - Off mode: the thermostat is disabled.
    - Three presets for the three clock programs available in the Remeha Home app.
    When a preset is selected, the integration will automatically switch the climate zone to auto mode to make sure the preset is applied.
- Each climate zone also exposes the following sensors/switches:
    - The next schedule setpoint
    - The time at which the next schedule setpoint gets activated
    - The current schedule setpoint
    - Switch to control fireplace mode
- Each hot water zone is exposed as a [water_heater](https://www.home-assistant.io/integrations/water_heater/) entity (see [DHW hot water control](#dhw-hot-water-control)), plus a sensor:
    - The water temperature
- Each appliance (CV-ketel) exposes the following sensors:
    - The water pressure

## DHW hot water control
Each hot water zone is exposed as a `water_heater` entity with the following
operation modes (service `water_heater.set_operation_mode`):

| Mode | Behaviour |
| --- | --- |
| `schedule` | Follow the DHW time program (alternates comfort/reduced periods). |
| `comfort` | Continuous comfort setpoint. |
| `boost` | Native ~30 minute heat boost, then the appliance auto-reverts to `schedule`. Duration is fixed by the appliance. |
| `off` | Anti-frost only. |

- **Target temperature** (`water_heater.set_temperature`) writes the comfort
  setpoint. (Reduced-setpoint control is intentionally omitted — the appliance
  rejects it with HTTP 400.)
- While a boost is running, the entity exposes a `boost_end` attribute with the
  UTC time at which the boost auto-ends.
- The mode icon changes with state: comfort `mdi:fire`, schedule `mdi:calendar`,
  boost `mdi:rocket-launch`.

Example — trigger a boost from an automation:
```yaml
service: water_heater.set_operation_mode
target:
  entity_id: water_heater.dhw
data:
  operation_mode: boost
```

## Installation

### Install this fork with HACS (DHW support)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=yoriaantje-dev&repository=remeha_home&category=integration)

Do you have [HACS](https://hacs.xyz/) installed?
Click the button above (it adds this fork as a custom repository), or add it manually:
1. HACS → Integrations → three-dot menu → **Custom repositories**
1. Repository: `https://github.com/yoriaantje-dev/remeha_home`, category **Integration**
1. Search integrations for **Remeha Home** and click `Download`
1. Restart Home Assistant
1. See [Setup](#setup)

### Install the original (upstream) with HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=msvisser&repository=remeha_home&category=integration)

The original integration by [@msvisser](https://github.com/msvisser) (without DHW control):
1. Search integrations for **Remeha Home**
1. Click `Install`
1. Restart Home Assistant
1. See [Setup](#setup)

### Install manually

1. Install this platform by creating a `custom_components` folder in the same folder as your configuration.yaml, if it doesn't already exist.
2. Create another folder `remeha_home` in the `custom_components` folder. Copy all files from `custom_components/remeha_home` into the `remeha_home` folder.

## Setup
1. In Home Assitant click on `Configuration`
1. Click on `Devices & Services`
1. Click on `+ Add integration`
1. Search for and select `Remeha Home`
1. Enter your email address and password
1. Click "Next"
1. Enjoy

## API documentation
For information on the Remeha Home API see [API documentation](documentation/api.md).
