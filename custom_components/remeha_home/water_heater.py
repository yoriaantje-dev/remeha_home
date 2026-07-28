"""Platform for water heater integration."""

from __future__ import annotations

import logging

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import RemehaHomeAPI
from .const import DOMAIN
from .coordinator import RemehaHomeUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Operation modes exposed to Home Assistant, using the familiar thermostat
# labels. Use these strings in automations, e.g.
# service water_heater.set_operation_mode -> operation_mode: heat
#   auto -> follow the DHW time program (the appliance's schedule)
#   heat -> continuous comfort setpoint
#   off  -> anti-frost; the appliance reports this as dhwZoneMode "Off"
# The native ~30 min boost is exposed separately as a switch (switch platform).
MODE_AUTO = "auto"
MODE_HEAT = "heat"
MODE_OFF = "off"

OPERATION_LIST = [MODE_AUTO, MODE_HEAT, MODE_OFF]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Remeha Home water heater entities from a config entry."""
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for appliance in coordinator.data["appliances"]:
        for hot_water_zone in appliance.get("hotWaterZones", []):
            entities.append(
                RemehaHomeWaterHeater(
                    api, coordinator, hot_water_zone["hotWaterZoneId"]
                )
            )

    async_add_entities(entities)


class RemehaHomeWaterHeater(CoordinatorEntity, WaterHeaterEntity):
    """Representation of a Remeha Home domestic hot water zone."""

    _attr_has_entity_name = True
    _attr_name = None  # take the device (zone) name, e.g. "DHW"
    _attr_translation_key = "dhw"  # icon translations live in icons.json
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list = OPERATION_LIST
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
    )

    def __init__(
        self,
        api: RemehaHomeAPI,
        coordinator: RemehaHomeUpdateCoordinator,
        hot_water_zone_id: str,
    ) -> None:
        """Create a Remeha Home water heater entity."""
        super().__init__(coordinator)
        self.api = api
        self.hot_water_zone_id = hot_water_zone_id
        self._attr_unique_id = "_".join([DOMAIN, hot_water_zone_id, "water_heater"])

    @property
    def _data(self):
        """Return the hot water zone data for this entity."""
        return self.coordinator.get_by_id(self.hot_water_zone_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this device."""
        return self.coordinator.get_device_info(self.hot_water_zone_id)

    @property
    def current_operation(self) -> str | None:
        """Return the current operation mode as a thermostat-style label.

        dhwZoneMode strings confirmed against live data:
        "ContinuousComfort" -> heat, "Scheduling" -> auto, "Off" -> off.
        "Boost" is transient and auto-reverts to the schedule, so it is shown
        as auto here; the boost switch tracks the boost itself. Matched
        case-insensitively; an unrecognised value falls back to off.
        """
        mode = (self._data.get("dhwZoneMode") or "").lower()
        if mode in ("continuouscomfort", "continuous-comfort", "comfort"):
            return MODE_HEAT
        # boost auto-reverts to schedule -> report auto while it runs
        if mode in ("scheduling", "schedule", "boost"):
            return MODE_AUTO
        # "off", "antifrost", "anti-frost", "eco", "frostprotection", ...
        return MODE_OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current hot water temperature, if the appliance reports it.

        A combi/on-demand appliance typically reports null while idle.
        """
        return self._data.get("dhwTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the comfort target temperature (the only settable setpoint)."""
        return self._data.get("comfortSetPoint")

    @property
    def min_temp(self) -> float:
        """Return the minimum settable comfort temperature."""
        ranges = self._data.get("setPointRanges") or {}
        return ranges.get("comfortSetpointMin", self._data.get("setPointMin", 35.0))

    @property
    def max_temp(self) -> float:
        """Return the maximum settable comfort temperature."""
        ranges = self._data.get("setPointRanges") or {}
        return ranges.get("comfortSetpointMax", self._data.get("setPointMax", 65.0))

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Switch the hot water zone to auto, heat or off mode."""
        if operation_mode == MODE_AUTO:
            await self.api.async_set_dhw_schedule(self.hot_water_zone_id)
        elif operation_mode == MODE_HEAT:
            await self.api.async_set_dhw_comfort(self.hot_water_zone_id)
        elif operation_mode == MODE_OFF:
            await self.api.async_set_dhw_off(self.hot_water_zone_id)
        else:
            raise ValueError(f"Unsupported operation mode: {operation_mode}")
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the comfort target temperature.

        Only the comfort setpoint is writable; the API rejects reduced-setpoint
        writes (400) for this appliance, so all temperature changes go to comfort.
        """
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.api.async_set_dhw_comfort_setpoint(
            self.hot_water_zone_id, temperature
        )
        await self.coordinator.async_request_refresh()
