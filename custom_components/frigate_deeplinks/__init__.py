"""Set up the Frigate Deep Links integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import services
from .api import FrigateApi, FrigateApiError
from .const import (
    CONF_LABELS,
    CONF_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    LOGGER,
)
from .coordinator import FrigateDeeplinksCoordinator
from .util import split_labels, tracked_pairs

PLATFORMS: list[Platform] = [Platform.EVENT, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one Frigate instance."""
    api = FrigateApi(
        async_get_clientsession(hass),
        entry.data[CONF_URL],
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
    )

    try:
        frigate_config = await api.async_get_config()
    except FrigateApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    options = {**entry.data, **entry.options}
    pairs = tracked_pairs(frigate_config, split_labels(options.get(CONF_LABELS)))
    if not pairs:
        raise ConfigEntryNotReady(
            "Frigate reported no cameras with tracked objects to follow"
        )

    coordinator = FrigateDeeplinksCoordinator(
        hass,
        entry,
        api,
        pairs,
        options.get(CONF_POLL_INTERVAL) or DEFAULT_POLL_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    services.async_register_services(hass)
    LOGGER.debug("Tracking %s camera/label pairs", len(pairs))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
