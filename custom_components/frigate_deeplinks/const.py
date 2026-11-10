"""Constants for the Frigate Deep Links integration."""

from __future__ import annotations

import logging

DOMAIN = "frigate_deeplinks"

LOGGER = logging.getLogger(__package__)

# Config / options keys
CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_POLL_INTERVAL = "poll_interval"
CONF_DASHBOARD = "dashboard"
CONF_VIEW = "view"
CONF_LABELS = "labels"

# Defaults
DEFAULT_URL = "http://ccab4aaf-frigate:5000"
DEFAULT_POLL_INTERVAL = 15
DEFAULT_DASHBOARD = "lovelace"
DEFAULT_VIEW = "camera"

MIN_POLL_INTERVAL = 5
MAX_POLL_INTERVAL = 300

# How far back the coordinator looks for events. Deep links only ever point at
# recent clips, so there is no point carrying weeks of history in memory.
HISTORY_HOURS = 48
MAX_EVENTS = 200
# How many events the "recent events" sensor exposes as an attribute list.
MAX_RECENT_EVENTS = 60

# Event media, served by Frigate itself.
MEDIA_THUMBNAIL = "thumbnail.jpg"
MEDIA_SNAPSHOT = "snapshot.jpg"
MEDIA_CLIP = "clip.mp4"

# Service names
SERVICE_URL = "url"

# Service fields
ATTR_EVENT_ID = "event_id"
ATTR_REVIEW_ID = "review_id"
ATTR_MEDIA = "media"
ATTR_DASHBOARD = "dashboard"
ATTR_VIEW = "view"
ATTR_CAMERA = "camera"

MEDIA_OPTIONS = ["clip", "snapshot"]
