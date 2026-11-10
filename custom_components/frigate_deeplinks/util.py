"""Small helpers shared by the coordinator and the services."""

from __future__ import annotations

from typing import Any

from .const import (
    DEFAULT_DASHBOARD,
    DEFAULT_VIEW,
    MEDIA_CLIP,
    MEDIA_OPTIONS,
    MEDIA_SNAPSHOT,
    MEDIA_THUMBNAIL,
)


def split_labels(value: str | list[str] | None) -> list[str]:
    """Normalize a comma separated label list (or a real list)."""
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        items = [str(item) for item in value]
    else:
        items = str(value).replace(";", ",").split(",")
    return [item.strip().lower() for item in items if item.strip()]


def tracked_pairs(
    frigate_config: dict[str, Any],
    label_filter: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Return the (camera, label) combinations worth tracking.

    Cameras with object detection disabled are skipped, and the labels come
    from Frigate's own ``objects.track`` list so the integration follows the
    user's Frigate configuration instead of guessing.
    """
    wanted = {label.strip().lower() for label in (label_filter or []) if label.strip()}
    pairs: list[tuple[str, str]] = []

    for camera, camera_config in (frigate_config.get("cameras") or {}).items():
        if not (camera_config or {}).get("enabled", True):
            continue
        if not (camera_config.get("detect") or {}).get("enabled", True):
            continue

        labels = ((camera_config.get("objects") or {}).get("track")) or []
        for label in labels:
            label = str(label).lower()
            if wanted and label not in wanted:
                continue
            pairs.append((camera, label))

    pairs.sort()
    return pairs


def normalize_event(event: dict[str, Any], review_ids: dict[str, str]) -> dict[str, Any]:
    """Reduce a Frigate event to the fields deep links actually need."""
    event_id = event.get("id")
    start = event.get("start_time")
    end = event.get("end_time")
    camera = event.get("camera")
    label = event.get("label")

    return {
        "id": event_id,
        "camera": camera,
        "label": label,
        "start": int(start) if start else None,
        "end": int(end) if end else None,
        "duration": round(end - start, 1) if start and end else None,
        "has_clip": bool(event.get("has_clip")),
        "has_snapshot": bool(event.get("has_snapshot")),
        "review_id": review_ids.get(event_id),
        "zones": event.get("zones") or [],
    }


def review_id_map(reviews: list[dict[str, Any]]) -> dict[str, str]:
    """Map event ID -> review ID using each review's detection list."""
    mapping: dict[str, str] = {}
    for review in reviews or []:
        review_id = review.get("id")
        if not review_id:
            continue
        detections = ((review.get("data") or {}).get("detections")) or []
        for event_id in detections:
            mapping.setdefault(event_id, review_id)
    return mapping


def build_view_path(
    *,
    dashboard: str | None,
    view: str | None,
    event_id: str | None,
    review_id: str | None,
    camera: str | None,
    media: str,
) -> str:
    """Build the Home Assistant path a dashboard card can consume.

    The resulting path works with any card that understands Frigate deep links
    (``?event=``, ``?review=``, ``?camera=``, ``?media=``); FrigateViewCard is
    the reference implementation.
    """
    dashboard = (dashboard or DEFAULT_DASHBOARD).strip("/")
    view = (view or DEFAULT_VIEW).strip("/")

    path = f"/{dashboard}/{view}" if dashboard else f"/{view}"

    params: list[str] = []
    if camera:
        params.append(f"camera={camera}")
    if event_id:
        params.append(f"event={event_id}")
    if review_id:
        params.append(f"review={review_id}")
    if media in MEDIA_OPTIONS:
        params.append(f"media={media}")

    if params:
        path = f"{path}?{'&'.join(params)}"
    return path


def media_paths(event_id: str) -> dict[str, str]:
    """Return the HA-side media paths for one event.

    These are served by the official Frigate integration's notification proxy,
    which is what makes them usable inside markdown cards and notifications.
    """
    return {
        MEDIA_THUMBNAIL: f"/api/frigate/notifications/{event_id}/{MEDIA_THUMBNAIL}",
        MEDIA_SNAPSHOT: f"/api/frigate/notifications/{event_id}/{MEDIA_SNAPSHOT}",
        MEDIA_CLIP: f"/api/frigate/notifications/{event_id}/{MEDIA_CLIP}",
    }
