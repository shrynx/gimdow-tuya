"""Config flow for Gimdow Lock integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

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
from .tuya_api import TuyaAPIError, TuyaCloudAPI

_LOGGER = logging.getLogger(__name__)

REGIONS = {
    "eu": "Europe",
    "us": "United States",
    "cn": "China",
    "in": "India",
}


class GimdowLockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gimdow Lock."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._region: str = "eu"
        self._devices: list[dict[str, Any]] = []
        self._api: TuyaCloudAPI | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._client_id = user_input[CONF_CLIENT_ID]
            self._client_secret = user_input[CONF_CLIENT_SECRET]
            self._region = user_input[CONF_REGION]

            # Validate credentials and get devices
            self._api = TuyaCloudAPI(
                self._client_id,
                self._client_secret,
                self._region,
            )

            try:
                await self._api.async_get_token()
                self._devices = await self._api.async_get_devices()

                if not self._devices:
                    errors["base"] = "no_devices"
                else:
                    return await self.async_step_select_device()
            except TuyaAPIError as err:
                _LOGGER.error("API error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"
            finally:
                if self._api and not self._devices:
                    await self._api.async_close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIENT_ID): str,
                    vol.Required(CONF_CLIENT_SECRET): str,
                    vol.Required(CONF_REGION, default="eu"): vol.In(REGIONS),
                }
            ),
            errors=errors,
            description_placeholders={
                "tuya_url": "https://iot.tuya.com",
            },
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]

            # Find the selected device
            device = next(
                (d for d in self._devices if d["id"] == device_id),
                None,
            )

            if device:
                # Check if already configured
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()

                if self._api:
                    await self._api.async_close()

                return self.async_create_entry(
                    title=device["name"],
                    data={
                        CONF_CLIENT_ID: self._client_id,
                        CONF_CLIENT_SECRET: self._client_secret,
                        CONF_REGION: self._region,
                        CONF_DEVICE_ID: device_id,
                        CONF_DEVICE_NAME: device["name"],
                    },
                )

        # Build device selection list
        device_options = {
            d["id"]: f"{d['name']} ({'Online' if d['online'] else 'Offline'})"
            for d in self._devices
        }

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): vol.In(device_options),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> GimdowLockOptionsFlow:
        """Get the options flow for this handler."""
        return GimdowLockOptionsFlow(config_entry)


class GimdowLockOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Gimdow Lock."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL, default=current_interval
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
                }
            ),
        )
