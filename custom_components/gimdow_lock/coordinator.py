"""Data coordinator for Gimdow Lock."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL, DEVICE_INFO_REFRESH_INTERVAL
from .tuya_api import TuyaAPIError, TuyaCloudAPI

_LOGGER = logging.getLogger(__name__)

# Delays (in seconds) for extra refreshes after a lock/unlock operation.
_POST_OPERATION_DELAYS = (10, 300)


class GimdowLockCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Gimdow Lock data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: TuyaCloudAPI,
        device_id: str,
        device_name: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api
        self.device_id = device_id
        self.device_name = device_name
        self.device_info: dict[str, Any] = {}
        self._device_info_last_refresh: float = 0
        self._scheduled_refreshes: list[CALLBACK_TYPE] = []

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Get device status
            status = await self.api.async_get_device_status(self.device_id)

            # Refresh device info periodically (for online status etc.)
            import time
            now = time.monotonic()
            if (
                not self.device_info
                or now - self._device_info_last_refresh > DEVICE_INFO_REFRESH_INTERVAL
            ):
                self.device_info = await self.api.async_get_device_info(self.device_id)
                self._device_info_last_refresh = now

            return {
                "status": status,
                "info": self.device_info,
                "online": self.device_info.get("online", False),
            }

        except TuyaAPIError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    def _cancel_scheduled_refreshes(self) -> None:
        """Cancel any pending post-operation refreshes."""
        for cancel in self._scheduled_refreshes:
            cancel()
        self._scheduled_refreshes.clear()

    def _schedule_delayed_refreshes(self) -> None:
        """Schedule extra refreshes after a lock/unlock operation."""
        self._cancel_scheduled_refreshes()

        for delay in _POST_OPERATION_DELAYS:
            @callback
            def _refresh(_now, _delay=delay) -> None:
                _LOGGER.debug(
                    "Post-operation refresh for %s (after %ss)", self.device_id, _delay
                )
                self.async_set_updated_data(self.data)  # trigger listeners
                self.hass.async_create_task(self.async_request_refresh())

            cancel = async_call_later(self.hass, delay, _refresh)
            self._scheduled_refreshes.append(cancel)

    async def async_unlock(self) -> bool:
        """Unlock the door."""
        result = await self.api.async_unlock(self.device_id)
        if result:
            self._schedule_delayed_refreshes()
        return result

    async def async_lock(self) -> bool:
        """Lock the door."""
        result = await self.api.async_lock(self.device_id)
        if result:
            self._schedule_delayed_refreshes()
        return result
