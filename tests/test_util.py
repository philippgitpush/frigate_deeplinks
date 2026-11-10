"""Tests for the pure helpers."""

from __future__ import annotations

from custom_components.frigate_deeplinks.util import (
    build_view_path,
    media_paths,
    normalize_event,
    review_id_map,
    split_labels,
    tracked_pairs,
)

FRIGATE_CONFIG = {
    "cameras": {
        "terassenkamera": {
            "enabled": True,
            "detect": {"enabled": True},
            "objects": {"track": ["person", "cat"]},
        },
        "garten": {
            "enabled": True,
            "detect": {"enabled": False},
            "objects": {"track": ["person"]},
        },
        "flur": {
            "enabled": True,
            "detect": {"enabled": True},
            "objects": {"track": ["person", "dog"]},
        },
    }
}


def test_split_labels() -> None:
    assert split_labels("Person, cat") == ["person", "cat"]
    assert split_labels("person;cat") == ["person", "cat"]
    assert split_labels(["Person", " Cat "]) == ["person", "cat"]
    assert split_labels("") == []
    assert split_labels(None) == []


def test_tracked_pairs_skips_disabled_detect() -> None:
    assert tracked_pairs(FRIGATE_CONFIG) == [
        ("flur", "dog"),
        ("flur", "person"),
        ("terassenkamera", "cat"),
        ("terassenkamera", "person"),
    ]


def test_tracked_pairs_respects_label_filter() -> None:
    assert tracked_pairs(FRIGATE_CONFIG, ["cat"]) == [("terassenkamera", "cat")]


def test_review_id_map() -> None:
    reviews = [
        {"id": "r1", "data": {"detections": ["e1", "e2"]}},
        {"id": "r2", "data": {"detections": ["e2", "e3"]}},
        {"id": "r3", "data": {}},
    ]
    assert review_id_map(reviews) == {"e1": "r1", "e2": "r1", "e3": "r2"}


def test_normalize_event() -> None:
    event = {
        "id": "e1",
        "camera": "terassenkamera",
        "label": "cat",
        "start_time": 1794295311.5,
        "end_time": 1794295326.5,
        "has_clip": True,
        "has_snapshot": True,
        "zones": ["terrasse"],
    }
    normalized = normalize_event(event, {"e1": "r1"})
    assert normalized["id"] == "e1"
    assert normalized["start"] == 1794295311
    assert normalized["duration"] == 15.0
    assert normalized["review_id"] == "r1"
    assert normalized["has_clip"] is True


def test_build_view_path() -> None:
    path = build_view_path(
        dashboard="dashboard-zuhause",
        view="kamera",
        event_id="e1",
        review_id="r1",
        camera="terassenkamera",
        media="clip",
    )
    assert path == (
        "/dashboard-zuhause/kamera?camera=terassenkamera&event=e1&review=r1&media=clip"
    )


def test_build_view_path_defaults() -> None:
    assert (
        build_view_path(
            dashboard=None,
            view=None,
            event_id="e1",
            review_id=None,
            camera=None,
            media="clip",
        )
        == "/lovelace/camera?event=e1&media=clip"
    )


def test_build_view_path_ignores_unknown_media() -> None:
    assert (
        build_view_path(
            dashboard="d",
            view="v",
            event_id="e1",
            review_id=None,
            camera=None,
            media="nope",
        )
        == "/d/v?event=e1"
    )


def test_media_paths() -> None:
    paths = media_paths("e1")
    assert paths["clip.mp4"] == "/api/frigate/notifications/e1/clip.mp4"
    assert paths["thumbnail.jpg"] == "/api/frigate/notifications/e1/thumbnail.jpg"
