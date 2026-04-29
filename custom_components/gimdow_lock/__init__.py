"""Gimdow Smart Lock integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_REGION,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    UPDATE_INTERVAL,
)
from .coordinator import GimdowLockCoordinator
from .tuya_api import TuyaCloudAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LOCK, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gimdow Lock from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API client
    api = TuyaCloudAPI(
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
        region=entry.data[CONF_REGION],
    )

    # Create coordinator with user-configured (or default) update interval
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, UPDATE_INTERVAL)
    coordinator = GimdowLockCoordinator(
        hass=hass,
        api=api,
        device_id=entry.data[CONF_DEVICE_ID],
        device_name=entry.data[CONF_DEVICE_NAME],
        update_interval=update_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Reload the entry when options change so the new interval takes effect.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: GimdowLockCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator._cancel_scheduled_refreshes()
        await coordinator.api.async_close()

    return unload_ok
