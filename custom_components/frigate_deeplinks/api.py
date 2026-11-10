"""Thin async client for the Frigate HTTP API.

Only the handful of endpoints needed for deep links are implemented. The client
is deliberately stateless apart from the optional access token, so it can be
shared by the config flow (validation) and the coordinator (polling).
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import LOGGER

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class FrigateApiError(Exception):
    """Frigate could not be reached, or answered with an error."""


class FrigateAuthError(FrigateApiError):
    """Frigate rejected our credentials."""


class FrigateApi:
    """Minimal Frigate REST client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._username = username or None
        self._password = password or None
        self._token: str | None = None

    @property
    def base_url(self) -> str:
        """Return the configured Frigate base URL."""
        return self._base_url

    def media_url(self, event_id: str, filename: str) -> str:
        """Return an absolute URL for one piece of event media."""
        return f"{self._base_url}/api/events/{event_id}/{filename}"

    # ------------------------------------------------------------------ http

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> Any:
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status in (401, 403):
                    if self._username and self._password and retry_auth:
                        await self.async_login()
                        return await self._request(
                            method, path, params=params, retry_auth=False
                        )
                    raise FrigateAuthError(
                        f"Authentication failed for {path} ({resp.status})"
                    )
                if resp.status >= 400:
                    body = (await resp.text())[:200]
                    raise FrigateApiError(
                        f"{method} {path} failed with {resp.status}: {body}"
                    )
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()
        except asyncio.TimeoutError as err:
            raise FrigateApiError(f"Timeout talking to Frigate at {self._base_url}") from err
        except aiohttp.ClientError as err:
            raise FrigateApiError(str(err)) from err

    async def async_login(self) -> None:
        """Authenticate against Frigate and keep the resulting token."""
        if not self._username or not self._password:
            raise FrigateAuthError("No credentials configured")

        try:
            async with self._session.post(
                f"{self._base_url}/api/login",
                json={"user": self._username, "password": self._password},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status >= 400:
                    raise FrigateAuthError(f"Login failed ({resp.status})")
                payload = await resp.json()
        except asyncio.TimeoutError as err:
            raise FrigateApiError("Timeout during Frigate login") from err
        except aiohttp.ClientError as err:
            raise FrigateApiError(str(err)) from err

        token = payload.get("access_token")
        if not token:
            raise FrigateAuthError("Login response did not contain a token")
        self._token = token
        LOGGER.debug("Authenticated against Frigate")

    # -------------------------------------------------------------- endpoints

    async def async_get_config(self) -> dict[str, Any]:
        """Return the Frigate configuration (camera and object settings)."""
        return await self._request("GET", "/api/config")

    async def async_get_events(
        self,
        *,
        cameras: list[str] | None = None,
        labels: list[str] | None = None,
        after: float | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return tracked object events, newest first."""
        params: dict[str, Any] = {"limit": limit, "include_thumbnails": 0}
        if cameras:
            params["cameras"] = ",".join(sorted(cameras))
        if labels:
            params["labels"] = ",".join(sorted(labels))
        if after is not None:
            params["after"] = int(after)
        return await self._request("GET", "/api/events", params=params)

    async def async_get_reviews(
        self,
        *,
        cameras: list[str] | None = None,
        after: float | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return reviews, which carry the review IDs needed for review links."""
        params: dict[str, Any] = {"limit": limit}
        if cameras:
            params["cameras"] = ",".join(sorted(cameras))
        if after is not None:
            params["after"] = int(after)
        return await self._request("GET", "/api/review", params=params)
