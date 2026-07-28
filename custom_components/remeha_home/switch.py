"""Platform for switch integration."""

from __future__ import annotations
import logging


from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import RemehaHomeAPI
from .const import DOMAIN
from .coordinator import RemehaHomeUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Remeha Home switch entities from a config entry."""
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for appliance in coordinator.data["appliances"]:
        for climate_zone in appliance["climateZones"]:
            climate_zone_id = climate_zone["climateZoneId"]

            entities.append(
                RemehaHomeFireplaceModeSwitch(api, coordinator, climate_zone_id)
            )

        for hot_water_zone in appliance.get("hotWaterZones", []):
            entities.append(
                RemehaHomeDHWBoostSwitch(
                    api, coordinator, hot_water_zone["hotWaterZoneId"]
                )
            )

    async_add_entities(entities)


class RemehaHomeSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        api: RemehaHomeAPI,
        coordinator: RemehaHomeUpdateCoordinator,
        climate_zone_id: str,
        entity_description: SwitchEntityDescription,
    ) -> None:
        """Create a Remeha Home switch entity."""
        super().__init__(coordinator)
        self.api = api
        self.climate_zone_id = climate_zone_id
        self.entity_description = entity_description

        self._attr_unique_id = "_".join(
            [DOMAIN, self.climate_zone_id, entity_description.key]
        )

    @property
    def _data(self):
        """Return the climate zone data for this switch."""
        return self.coordinator.get_by_id(self.climate_zone_id)

    @property
    def is_on(self) -> bool:
        """Return the state of this switch."""
        return self._data[self.entity_description.key]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this device."""
        return self.coordinator.get_device_info(self.climate_zone_id)


class RemehaHomeFireplaceModeSwitch(RemehaHomeSwitch):
    """Representation of a fireplace mode switch."""

    def __init__(
        self,
        api: RemehaHomeAPI,
        coordinator: RemehaHomeUpdateCoordinator,
        climate_zone_id: str,
    ) -> None:
        """Create a Remeha Home fireplace mode switch entity."""
        super().__init__(
            api,
            coordinator,
            climate_zone_id,
            SwitchEntityDescription(
                key="firePlaceModeActive",
                name="Fireplace Mode",
                device_class=SwitchDeviceClass.SWITCH,
            ),
        )

    @property
    def icon(self):
        """Return the icon for this switch."""
        if self.is_on:
            return "mdi:fireplace"
        return "mdi:fireplace-off"

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        _LOGGER.debug("Enable fireplace mode")
        await self.api.async_set_fireplace_mode(self.climate_zone_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        _LOGGER.debug("Disable fireplace mode")
        await self.api.async_set_fireplace_mode(self.climate_zone_id, False)
        await self.coordinator.async_request_refresh()


class RemehaHomeDHWBoostSwitch(CoordinatorEntity, SwitchEntity):
    """Toggle switch for the domestic hot water boost.

    On activates the native ~30 min boost (POST /modes/boost). The appliance
    ends the boost automatically after its fixed duration; turning the switch
    off early returns the zone to its schedule.
    """

    _attr_has_entity_name = True
    _attr_name = "Boost"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        api: RemehaHomeAPI,
        coordinator: RemehaHomeUpdateCoordinator,
        hot_water_zone_id: str,
    ) -> None:
        """Create a Remeha Home DHW boost switch entity."""
        super().__init__(coordinator)
        self.api = api
        self.hot_water_zone_id = hot_water_zone_id
        self._attr_unique_id = "_".join([DOMAIN, hot_water_zone_id, "dhw_boost"])

    @property
    def _data(self):
        """Return the hot water zone data for this switch."""
        return self.coordinator.get_by_id(self.hot_water_zone_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this device."""
        return self.coordinator.get_device_info(self.hot_water_zone_id)

    @property
    def is_on(self) -> bool:
        """Return whether a boost is currently running."""
        return (self._data.get("dhwZoneMode") or "").lower() == "boost"

    @property
    def icon(self) -> str:
        """Return the icon for this switch."""
        return "mdi:rocket-launch" if self.is_on else "mdi:rocket-launch-outline"

    @property
    def extra_state_attributes(self) -> dict | None:
        """Expose the boost auto-end time while a boost is running."""
        end = self._data.get("boostModeEndTime")
        if self.is_on and end:
            return {"boost_end": end}
        return None

    async def async_turn_on(self, **kwargs):
        """Start a hot water boost."""
        _LOGGER.debug("Activate DHW boost")
        await self.api.async_set_dhw_boost(self.hot_water_zone_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Stop the boost by returning the zone to its schedule."""
        _LOGGER.debug("Cancel DHW boost -> schedule")
        await self.api.async_set_dhw_schedule(self.hot_water_zone_id)
        await self.coordinator.async_request_refresh()
