"""Services that hand out ready-to-use Frigate deep links."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import (
    ATTR_CAMERA,
    ATTR_DASHBOARD,
    ATTR_EVENT_ID,
    ATTR_MEDIA,
    ATTR_REVIEW_ID,
    ATTR_VIEW,
    DEFAULT_DASHBOARD,
    DEFAULT_VIEW,
    DOMAIN,
    MEDIA_CLIP,
    MEDIA_OPTIONS,
    MEDIA_SNAPSHOT,
    MEDIA_THUMBNAIL,
    SERVICE_URL,
)
from .coordinator import FrigateDeeplinksCoordinator
from .util import build_view_path, media_paths

SERVICE_URL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_EVENT_ID): cv.string,
        vol.Optional(ATTR_REVIEW_ID): cv.string,
        vol.Optional(ATTR_MEDIA, default=MEDIA_CLIP): vol.In(MEDIA_OPTIONS),
        vol.Optional(ATTR_DASHBOARD): cv.string,
        vol.Optional(ATTR_VIEW): cv.string,
        vol.Optional(ATTR_CAMERA): cv.string,
    }
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register the integration services exactly once."""
    if hass.services.has_service(DOMAIN, SERVICE_URL):
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_URL,
        _async_handle_url,
        schema=SERVICE_URL_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def _coordinators(hass: HomeAssistant) -> list[FrigateDeeplinksCoordinator]:
    """Return every loaded coordinator."""
    return [
        coordinator
        for coordinator in (hass.data.get(DOMAIN) or {}).values()
        if isinstance(coordinator, FrigateDeeplinksCoordinator)
    ]


def _absolute_url(hass: HomeAssistant, path: str) -> str | None:
    """Turn a relative path into an absolute URL when HA knows one."""
    try:
        return f"{get_url(hass, prefer_external=True, allow_cloud=False)}{path}"
    except NoURLAvailableError:
        return None


async def _async_handle_url(call: ServiceCall) -> dict[str, Any]:
    """Build a deep link for an event or review."""
    event_id: str | None = call.data.get(ATTR_EVENT_ID)
    review_id: str | None = call.data.get(ATTR_REVIEW_ID)
    media: str = call.data.get(ATTR_MEDIA, MEDIA_CLIP)
    camera: str | None = call.data.get(ATTR_CAMERA)

    if not event_id and not review_id:
        raise ServiceValidationError("Provide event_id or review_id")

    coordinators = _coordinators(hass=call.hass)
    event: dict[str, Any] | None = None
    for coordinator in coordinators:
        event = (
            coordinator.find_event(event_id)
            if event_id
            else coordinator.find_event_by_review(review_id or "")
        )
        if event:
            break

    if event:
        event_id = event["id"]
        review_id = review_id or event.get("review_id")
        camera = camera or event["camera"] or None

    coordinator = coordinators[0] if coordinators else None
    dashboard = call.data.get(ATTR_DASHBOARD) or (
        coordinator.dashboard if coordinator else DEFAULT_DASHBOARD
    )
    view = call.data.get(ATTR_VIEW) or (coordinator.view if coordinator else DEFAULT_VIEW)

    path = build_view_path(
        dashboard=dashboard,
        view=view,
        event_id=event_id,
        review_id=review_id,
        camera=camera,
        media=media,
    )

    result: dict[str, Any] = {
        "path": path,
        "url": _absolute_url(call.hass, path),
        "event_id": event_id,
        "review_id": review_id,
        "camera": camera,
        "media": media,
    }

    if event_id:
        paths = media_paths(event_id)
        result["thumbnail_path"] = paths[MEDIA_THUMBNAIL]
        result["snapshot_path"] = paths[MEDIA_SNAPSHOT]
        result["clip_path"] = paths[MEDIA_CLIP]

    return result
