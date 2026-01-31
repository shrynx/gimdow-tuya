"""Lock platform for Gimdow Lock."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, CONF_DEVICE_NAME, DOMAIN
from .coordinator import GimdowLockCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gimdow Lock from a config entry."""
    coordinator: GimdowLockCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        GimdowLock(
            coordinator=coordinator,
            device_id=entry.data[CONF_DEVICE_ID],
            device_name=entry.data[CONF_DEVICE_NAME],
        )
    ])


class GimdowLock(CoordinatorEntity[GimdowLockCoordinator], LockEntity):
    """Representation of a Gimdow Lock."""

    _attr_has_entity_name = True
    _attr_name = None  # Use device name
    _attr_supported_features = LockEntityFeature(0)
    _attr_icon = "mdi:lock"

    def __init__(
        self,
        coordinator: GimdowLockCoordinator,
        device_id: str,
        device_name: str,
    ) -> None:
        """Initialize the lock."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._attr_unique_id = f"{device_id}_lock"
        self._is_locking = False
        self._is_unlocking = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        info = self.coordinator.device_info
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="Gimdow",
            model=info.get("product_id", "Smart Lock"),
            sw_version=info.get("firmware_version"),
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data.get("online", False)

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""
        status = self.coordinator.data.get("status", {})

        # Check lock_motor_state (False = locked, True = unlocked/motor active)
        if "lock_motor_state" in status:
            return not status["lock_motor_state"]

        # Fallback to other possible status codes
        if "closed_opened" in status:
            return status["closed_opened"] == "closed"

        return None

    @property
    def icon(self) -> str:
        """Return the icon based on lock state."""
        if self.is_locked is None:
            return "mdi:lock-question"
        return "mdi:lock" if self.is_locked else "mdi:lock-open"

    @property
    def is_locking(self) -> bool:
        """Return true if lock is locking."""
        return self._is_locking

    @property
    def is_unlocking(self) -> bool:
        """Return true if lock is unlocking."""
        return self._is_unlocking

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the door."""
        self._is_locking = True
        self.async_write_ha_state()

        try:
            await self.coordinator.async_lock()
        finally:
            self._is_locking = False
            self.async_write_ha_state()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the door."""
        self._is_unlocking = True
        self.async_write_ha_state()

        try:
            await self.coordinator.async_unlock()
        finally:
            self._is_unlocking = False
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
