"""Event entities that expose the latest detection per camera and label.

This is the piece the official Frigate integration does not provide: the
``event_id`` (and the related review ID) of the newest detection, which is what
a dashboard card needs to open the matching clip.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MEDIA_CLIP, MEDIA_SNAPSHOT, MEDIA_THUMBNAIL
from .coordinator import FrigateDeeplinksCoordinator
from .entity import FrigateDeeplinksEntity
from .util import build_view_path, media_paths

EVENT_TYPE_DETECTION = "detection"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one event entity per tracked camera/label pair."""
    coordinator: FrigateDeeplinksCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        FrigateLastEventEntity(coordinator, camera, label)
        for camera, label in coordinator.pairs
    )


class FrigateLastEventEntity(FrigateDeeplinksEntity, EventEntity):
    """Latest detection for one camera label."""

    _attr_event_types = [EVENT_TYPE_DETECTION]
    _attr_translation_key = "last_event"

    def __init__(
        self,
        coordinator: FrigateDeeplinksCoordinator,
        camera: str,
        label: str,
    ) -> None:
        super().__init__(coordinator, camera, f"last_event_{label}")
        self._label = label
        self._attr_translation_placeholders = {"label": label.title()}
        self._attr_extra_state_attributes = {}
        self._last_event_id: str | None = None
        self._initialized = False

    async def async_added_to_hass(self) -> None:
        """Adopt the current event silently so setup does not fire it."""
        event = self.coordinator.latest_for(self._camera, self._label)
        if event:
            self._last_event_id = event["id"]
            self._attr_extra_state_attributes = self._describe(event)
        self._initialized = True
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fire the entity when a new event shows up, refresh attributes."""
        event = self.coordinator.latest_for(self._camera, self._label)
        if event:
            attributes = self._describe(event)
            if self._initialized and event["id"] != self._last_event_id:
                self._last_event_id = event["id"]
                self._attr_extra_state_attributes = attributes
                self._trigger_event(EVENT_TYPE_DETECTION, dict(attributes))
            elif attributes != self._attr_extra_state_attributes:
                self._attr_extra_state_attributes = attributes
        super()._handle_coordinator_update()

    def _describe(self, event: dict[str, Any]) -> dict[str, Any]:
        """Turn a normalized event into entity attributes."""
        media = media_paths(event["id"])
        common = {
            "dashboard": self.coordinator.dashboard,
            "view": self.coordinator.view,
            "camera": event["camera"],
        }
        return {
            "event_id": event["id"],
            "review_id": event.get("review_id"),
            "camera": event["camera"],
            "label": event["label"],
            "start": _iso(event.get("start")),
            "end": _iso(event.get("end")),
            "duration": event.get("duration"),
            "has_clip": event["has_clip"],
            "has_snapshot": event["has_snapshot"],
            "zones": event.get("zones") or [],
            "deep_link": build_view_path(
                dashboard=common["dashboard"],
                view=common["view"],
                event_id=event["id"],
                review_id=event.get("review_id"),
                camera=common["camera"],
                media="clip",
            ),
            "deep_link_snapshot": build_view_path(
                dashboard=common["dashboard"],
                view=common["view"],
                event_id=event["id"],
                review_id=event.get("review_id"),
                camera=common["camera"],
                media="snapshot",
            ),
            "thumbnail_path": media[MEDIA_THUMBNAIL],
            "snapshot_path": media[MEDIA_SNAPSHOT],
            "clip_path": media[MEDIA_CLIP],
        }


def _iso(timestamp: int | None) -> str | None:
    """Convert an epoch timestamp to an ISO string."""
    if not timestamp:
        return None
    return dt_util.utc_from_timestamp(timestamp).isoformat()
