"""Sensor platform for Gimdow Lock."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, CONF_DEVICE_NAME, DOMAIN
from .coordinator import GimdowLockCoordinator

_LOGGER = logging.getLogger(__name__)

BATTERY_LEVEL_MAP = {
    "high": 100,
    "medium": 50,
    "low": 20,
    "poweroff": 0,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gimdow Lock sensors from a config entry."""
    coordinator: GimdowLockCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = entry.data[CONF_DEVICE_ID]
    device_name = entry.data[CONF_DEVICE_NAME]

    entities = [
        GimdowBatterySensor(coordinator, device_id, device_name),
    ]

    async_add_entities(entities)


class GimdowBatterySensor(CoordinatorEntity[GimdowLockCoordinator], SensorEntity):
    """Battery sensor for Gimdow Lock."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = "%"

    entity_description = SensorEntityDescription(
        key="battery",
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement="%",
    )

    def __init__(
        self,
        coordinator: GimdowLockCoordinator,
        device_id: str,
        device_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._attr_unique_id = f"{device_id}_battery"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        info = self.coordinator.device_info
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="Gimdow",
            model=info.get("product_id", "Smart Lock"),
        )

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        status = self.coordinator.data.get("status", {})
        battery_state = status.get("battery_state")

        if battery_state is None:
            return None

        return BATTERY_LEVEL_MAP.get(battery_state, 50)

    @property
    def icon(self) -> str:
        """Return the icon based on battery level."""
        level = self.native_value
        if level is None:
            return "mdi:battery-unknown"
        if level >= 90:
            return "mdi:battery"
        if level >= 70:
            return "mdi:battery-80"
        if level >= 50:
            return "mdi:battery-60"
        if level >= 30:
            return "mdi:battery-40"
        if level >= 10:
            return "mdi:battery-20"
        return "mdi:battery-alert"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
