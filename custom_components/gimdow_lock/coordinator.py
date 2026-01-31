"""Data coordinator for Gimdow Lock."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL
from .tuya_api import TuyaAPIError, TuyaCloudAPI

_LOGGER = logging.getLogger(__name__)


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

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Get device status
            status = await self.api.async_get_device_status(self.device_id)

            # Get device info (less frequently needed, but useful)
            if not self.device_info:
                self.device_info = await self.api.async_get_device_info(self.device_id)

            return {
                "status": status,
                "info": self.device_info,
                "online": self.device_info.get("online", False),
            }

        except TuyaAPIError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    async def async_unlock(self) -> bool:
        """Unlock the door."""
        result = await self.api.async_unlock(self.device_id)
        if result:
            await self.async_request_refresh()
        return result

    async def async_lock(self) -> bool:
        """Lock the door."""
        result = await self.api.async_lock(self.device_id)
        if result:
            await self.async_request_refresh()
        return result
