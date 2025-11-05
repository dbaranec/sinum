"""DataUpdateCoordinator for Sinum integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SinumAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)


class SinumDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Sinum API."""

    def __init__(self, hass: HomeAssistant, api: SinumAPI) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        try:
            rooms = await self.api.async_get_rooms()
            # Convert rooms list to dict for easier access
            return {room["id"]: room for room in rooms}
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

