"""Base entity for Frigate Deep Links."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FrigateDeeplinksCoordinator


class FrigateDeeplinksEntity(CoordinatorEntity[FrigateDeeplinksCoordinator]):
    """Entity bound to one Frigate camera."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FrigateDeeplinksCoordinator,
        camera: str,
        suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._camera = camera
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{camera}_{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.entry.entry_id}_{camera}")},
            name=camera,
            manufacturer="Frigate",
            model="Deep Links",
        )

    @property
    def available(self) -> bool:
        """Return True while the coordinator has data."""
        return super().available and self.coordinator.data is not None
