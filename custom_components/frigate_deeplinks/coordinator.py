"""Coordinator that keeps the recent Frigate events used for deep links."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import FrigateApi, FrigateApiError
from .const import (
    CONF_DASHBOARD,
    CONF_VIEW,
    DEFAULT_DASHBOARD,
    DEFAULT_VIEW,
    DOMAIN,
    HISTORY_HOURS,
    LOGGER,
    MAX_EVENTS,
)
from .util import normalize_event, review_id_map

CoordinatorData = dict[str, Any]


class FrigateDeeplinksCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Poll Frigate and expose the latest event per (camera, label)."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: FrigateApi,
        pairs: list[tuple[str, str]],
        poll_interval: int,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}:{entry.title}",
            update_interval=timedelta(seconds=poll_interval),
        )
        self.entry = entry
        self.api = api
        self.pairs = pairs
        self.cameras = sorted({camera for camera, _ in pairs})
        self.labels = sorted({label for _, label in pairs})

        options = {**entry.data, **entry.options}
        self.dashboard = (options.get(CONF_DASHBOARD) or DEFAULT_DASHBOARD).strip("/")
        self.view = (options.get(CONF_VIEW) or DEFAULT_VIEW).strip("/")

    async def _async_update_data(self) -> CoordinatorData:
        now = dt_util.utcnow().timestamp()
        after = now - HISTORY_HOURS * 3600

        try:
            events = await self.api.async_get_events(
                cameras=self.cameras,
                labels=self.labels,
                after=after,
                limit=MAX_EVENTS,
            )
            reviews = await self.api.async_get_reviews(cameras=self.cameras, after=after)
        except FrigateApiError as err:
            raise UpdateFailed(str(err)) from err

        review_ids = review_id_map(reviews)

        normalized: list[dict[str, Any]] = [
            normalize_event(event, review_ids) for event in events or []
        ]
        normalized.sort(key=lambda item: item["start"] or 0, reverse=True)

        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for event in normalized:
            key = (event["camera"], event["label"])
            if key in latest:
                continue
            if key in self.pairs:
                latest[key] = event

        return {"events": normalized, "latest": latest, "generated": now}

    # ---------------------------------------------------------------- helpers

    def events_for_camera(self, camera: str) -> list[dict[str, Any]]:
        """Return all recent events for a camera, newest first."""
        return [
            event
            for event in (self.data or {}).get("events", [])
            if event["camera"] == camera
        ]

    def latest_for(self, camera: str, label: str) -> dict[str, Any] | None:
        """Return the newest event for a camera/label pair, if any."""
        return (self.data or {}).get("latest", {}).get((camera, label))

    def find_event(self, event_id: str) -> dict[str, Any] | None:
        """Look up one event by ID."""
        for event in (self.data or {}).get("events", []):
            if event["id"] == event_id:
                return event
        return None

    def find_event_by_review(self, review_id: str) -> dict[str, Any] | None:
        """Look up the newest event belonging to a review."""
        for event in (self.data or {}).get("events", []):
            if event["review_id"] == review_id:
                return event
        return None
