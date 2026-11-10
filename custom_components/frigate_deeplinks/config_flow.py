"""Config and options flow for Frigate Deep Links."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FrigateApi, FrigateApiError, FrigateAuthError
from .const import (
    CONF_DASHBOARD,
    CONF_LABELS,
    CONF_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    CONF_VIEW,
    DEFAULT_DASHBOARD,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_URL,
    DEFAULT_VIEW,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
)
from .util import split_labels, tracked_pairs

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): cv.string,
        vol.Optional(CONF_USERNAME, default=""): cv.string,
        vol.Optional(CONF_PASSWORD, default=""): cv.string,
        vol.Optional(
            CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
        ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL)),
        vol.Optional(CONF_DASHBOARD, default=DEFAULT_DASHBOARD): cv.string,
        vol.Optional(CONF_VIEW, default=DEFAULT_VIEW): cv.string,
        vol.Optional(CONF_LABELS, default=""): cv.string,
    }
)


def _normalize_url(value: str) -> str:
    """Turn ``host:5000`` into a usable base URL."""
    url = value.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url


class FrigateDeeplinksConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the Frigate URL and validate it."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input = dict(user_input)
            user_input[CONF_URL] = _normalize_url(user_input[CONF_URL])

            api = FrigateApi(
                async_get_clientsession(self.hass),
                user_input[CONF_URL],
                user_input.get(CONF_USERNAME),
                user_input.get(CONF_PASSWORD),
            )

            try:
                frigate_config = await api.async_get_config()
            except FrigateAuthError:
                errors["base"] = "invalid_auth"
            except FrigateApiError:
                errors["base"] = "cannot_connect"
            else:
                if not tracked_pairs(frigate_config, split_labels(user_input.get(CONF_LABELS))):
                    errors["base"] = "no_cameras"
                else:
                    await self.async_set_unique_id(user_input[CONF_URL])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Frigate Deep Links", data=user_input
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input or {}
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return FrigateDeeplinksOptionsFlow()


class FrigateDeeplinksOptionsFlow(OptionsFlow):
    """Adjust polling and link targets without re-adding the integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options form."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_POLL_INTERVAL,
                    default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL),
                ),
                vol.Optional(
                    CONF_DASHBOARD,
                    default=options.get(CONF_DASHBOARD, DEFAULT_DASHBOARD),
                ): cv.string,
                vol.Optional(
                    CONF_VIEW, default=options.get(CONF_VIEW, DEFAULT_VIEW)
                ): cv.string,
                vol.Optional(
                    CONF_LABELS, default=options.get(CONF_LABELS, "")
                ): cv.string,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
