"""Diagnostics support for Frigate Deep Links."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, DOMAIN
from .coordinator import FrigateDeeplinksCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: FrigateDeeplinksCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    latest = data.get("latest", {})

    return {
        "entry": {
            "data": {
                key: "**REDACTED**" if key == CONF_PASSWORD else value
                for key, value in entry.data.items()
            },
            "options": dict(entry.options),
        },
        "tracked_pairs": coordinator.pairs,
        "dashboard": coordinator.dashboard,
        "view": coordinator.view,
        "event_count": len(data.get("events", [])),
        "latest_events": {
            f"{camera}/{label}": event["id"] for (camera, label), event in latest.items()
        },
    }
