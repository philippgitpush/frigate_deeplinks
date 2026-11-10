"""Sensor exposing the recent event list per camera.

This mirrors what the dashboard thumbnail row needs, so the row can stop
depending on a hand-rolled MQTT feed.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MAX_RECENT_EVENTS, MEDIA_THUMBNAIL
from .coordinator import FrigateDeeplinksCoordinator
from .entity import FrigateDeeplinksEntity
from .util import build_view_path, media_paths


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one recent-events sensor per camera."""
    coordinator: FrigateDeeplinksCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        FrigateRecentEventsSensor(coordinator, camera) for camera in coordinator.cameras
    )


class FrigateRecentEventsSensor(FrigateDeeplinksEntity, SensorEntity):
    """Number of recent events, with the list as an attribute."""

    _attr_translation_key = "recent_events"
    _attr_icon = "mdi:movie-open-play"

    def __init__(
        self,
        coordinator: FrigateDeeplinksCoordinator,
        camera: str,
    ) -> None:
        super().__init__(coordinator, camera, "recent_events")

    @property
    def native_value(self) -> int:
        """Return the number of recent events for this camera."""
        return len(self.coordinator.events_for_camera(self._camera))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the event list, newest first."""
        events = self.coordinator.events_for_camera(self._camera)
        return {
            "count": len(events),
            "newest": events[0]["start"] if events else None,
            "oldest": events[-1]["start"] if events else None,
            "events": [
                self._event_summary(event) for event in events[:MAX_RECENT_EVENTS]
            ],
        }

    def _event_summary(self, event: dict[str, Any]) -> dict[str, Any]:
        """Return a compact, template-friendly event description."""
        media = media_paths(event["id"])
        return {
            "id": event["id"],
            "camera": event["camera"],
            "label": event["label"],
            "start": event["start"],
            "end": event.get("end"),
            "review_id": event.get("review_id"),
            "has_clip": event["has_clip"],
            "thumbnail_path": media[MEDIA_THUMBNAIL],
            "deep_link": build_view_path(
                dashboard=self.coordinator.dashboard,
                view=self.coordinator.view,
                event_id=event["id"],
                review_id=event.get("review_id"),
                camera=event["camera"],
                media="clip",
            ),
        }
