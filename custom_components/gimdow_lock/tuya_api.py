"""Tuya Cloud API client for Gimdow Lock."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import aiohttp

from .const import LOCK_CATEGORIES, TUYA_REGIONS

_LOGGER = logging.getLogger(__name__)


class TuyaAPIError(Exception):
    """Tuya API error."""

    def __init__(self, code: str | int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Tuya API Error {code}: {message}")


class TuyaCloudAPI:
    """Tuya Cloud API client."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        region: str = "eu",
    ) -> None:
        """Initialize the API client."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = TUYA_REGIONS.get(region, TUYA_REGIONS["eu"])
        self._access_token: str | None = None
        self._token_expiry: float = 0
        self._refresh_token: str | None = None
        self._session: aiohttp.ClientSession | None = None
        self._uid: str | None = None

    def _sign(self, message: str) -> str:
        """Calculate HMAC-SHA256 signature."""
        return hmac.new(
            self.client_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest().upper()

    def _build_headers(
        self,
        method: str,
        path: str,
        body: str = "",
        with_token: bool = True,
    ) -> dict[str, str]:
        """Build request headers with signature."""
        t = str(int(time.time() * 1000))
        content_hash = hashlib.sha256(body.encode() if body else b"").hexdigest()
        sign_str = f"{method}\n{content_hash}\n\n{path}"

        if with_token and self._access_token:
            msg = self.client_id + self._access_token + t + sign_str
        else:
            msg = self.client_id + t + sign_str

        headers = {
            "client_id": self.client_id,
            "sign": self._sign(msg),
            "t": t,
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json",
        }

        if with_token and self._access_token:
            headers["access_token"] = self._access_token

        return headers

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        with_token: bool = True,
    ) -> dict[str, Any]:
        """Make an API request."""
        session = await self._ensure_session()
        url = f"{self.base_url}{path}"
        body = json.dumps(data) if data else ""
        headers = self._build_headers(method, path, body, with_token)

        try:
            if method == "GET":
                async with session.get(url, headers=headers) as resp:
                    result = await resp.json()
            else:
                async with session.post(url, headers=headers, data=body or None) as resp:
                    result = await resp.json()

            if not result.get("success"):
                raise TuyaAPIError(
                    result.get("code", "unknown"),
                    result.get("msg", "Unknown error"),
                )

            return result

        except aiohttp.ClientError as err:
            raise TuyaAPIError("connection_error", str(err)) from err

    async def async_get_token(self) -> None:
        """Ensure we have a valid access token.

        Raises TuyaAPIError if the token cannot be obtained.
        """
        if time.time() < self._token_expiry - 60:
            return

        result = await self._request(
            "GET",
            "/v1.0/token?grant_type=1",
            with_token=False,
        )
        token_data = result["result"]
        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token")
        self._token_expiry = time.time() + token_data.get("expire_time", 7200)
        self._uid = token_data.get("uid")
        _LOGGER.debug("Token obtained successfully")

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Get all devices (filtered to locks only)."""
        await self.async_get_token()

        result = await self._request(
            "GET",
            "/v1.0/iot-01/associated-users/devices",
        )
        devices = result.get("result", {}).get("devices", [])

        # Filter to lock devices only
        locks = [
            {
                "id": d.get("id"),
                "name": d.get("name", "Unknown Lock"),
                "category": d.get("category"),
                "online": d.get("online", False),
                "product_id": d.get("product_id"),
            }
            for d in devices
            if d.get("category") in LOCK_CATEGORIES
        ]

        _LOGGER.debug("Found %d lock(s)", len(locks))
        return locks

    async def async_get_device_status(self, device_id: str) -> dict[str, Any]:
        """Get device status.

        Raises TuyaAPIError on failure so the coordinator can mark the
        update as failed instead of silently returning empty data.
        """
        await self.async_get_token()

        result = await self._request("GET", f"/v1.0/devices/{device_id}/status")
        status = {}
        for dp in result.get("result", []):
            status[dp.get("code")] = dp.get("value")
        _LOGGER.debug("Device %s status: %s", device_id, status)
        return status

    async def async_get_device_info(self, device_id: str) -> dict[str, Any]:
        """Get device info.

        Raises TuyaAPIError on failure so callers can handle it.
        """
        await self.async_get_token()

        result = await self._request("GET", f"/v1.0/devices/{device_id}")
        return result.get("result", {})

    async def async_get_open_logs(
        self, device_id: str, minutes: int = 10
    ) -> list[dict[str, Any]]:
        """Get recent door lock open/close logs.

        Returns a list of log entries, most recent first.
        Each entry has 'status' (dict with 'code' and 'value') and 'update_time'.
        """
        await self.async_get_token()

        now_ms = int(time.time() * 1000)
        start_ms = now_ms - (minutes * 60 * 1000)
        path = (
            f"/v1.0/devices/{device_id}/door-lock/open-logs"
            f"?page_no=1&page_size=5&start_time={start_ms}&end_time={now_ms}"
        )
        result = await self._request("GET", path)
        logs = result.get("result", {}).get("logs", [])
        _LOGGER.debug("Open logs for %s: %s", device_id, logs)
        return logs

    async def _get_password_ticket(self, device_id: str) -> str | None:
        """Get password ticket for lock operations."""
        try:
            result = await self._request(
                "POST",
                f"/v1.0/devices/{device_id}/door-lock/password-ticket",
            )
            return result.get("result", {}).get("ticket_id")
        except TuyaAPIError as err:
            _LOGGER.error("Failed to get password ticket: %s", err)
            return None

    async def async_unlock(self, device_id: str) -> bool:
        """Unlock the door."""
        await self.async_get_token()

        ticket_id = await self._get_password_ticket(device_id)
        if not ticket_id:
            return False

        try:
            # Try password-free open-door first
            result = await self._request(
                "POST",
                f"/v1.0/devices/{device_id}/door-lock/password-free/open-door",
                {"ticket_id": ticket_id},
            )
            _LOGGER.info("Door unlocked successfully")
            return True
        except TuyaAPIError:
            pass

        try:
            # Fallback to door-operate endpoint
            result = await self._request(
                "POST",
                f"/v1.0/smart-lock/devices/{device_id}/password-free/door-operate",
                {"ticket_id": ticket_id, "open": "true"},
            )
            _LOGGER.info("Door unlocked successfully (via door-operate)")
            return True
        except TuyaAPIError as err:
            _LOGGER.error("Failed to unlock: %s", err)
            return False

    async def async_lock(self, device_id: str) -> bool:
        """Lock the door."""
        await self.async_get_token()

        ticket_id = await self._get_password_ticket(device_id)
        if not ticket_id:
            return False

        try:
            result = await self._request(
                "POST",
                f"/v1.0/smart-lock/devices/{device_id}/password-free/door-operate",
                {"ticket_id": ticket_id, "open": "false"},
            )
            _LOGGER.info("Door locked successfully")
            return True
        except TuyaAPIError as err:
            _LOGGER.error("Failed to lock: %s", err)
            return False

    async def async_close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
