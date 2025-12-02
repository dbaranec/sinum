"""Binary sensor platform for Sinum integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_ROOM_ID, ATTR_ROOM_NAME, DOMAIN
from .coordinator import SinumDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sinum binary sensor platform."""
    api = hass.data[DOMAIN][entry.entry_id]
    coordinator = SinumDataUpdateCoordinator(hass, api)
    
    # Fetch initial data so we have data to create entities
    await coordinator.async_config_entry_first_refresh()
    
    entities = []
    for room_id, room_data in coordinator.data.items():
        # Add heating binary sensor for all rooms (will show False if not available)
        entities.append(SinumHeatingBinarySensor(coordinator, room_id, room_data))
        # Add cooling binary sensor for all rooms (will show False if not available)
        entities.append(SinumCoolingBinarySensor(coordinator, room_id, room_data))
    
    async_add_entities(entities)


class SinumHeatingBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Sinum heating circuit binary sensor."""

    def __init__(
        self,
        coordinator: SinumDataUpdateCoordinator,
        room_id: str | int,
        room_data: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._room_id = room_id
        self._room_name = room_data.get("name", f"Room {room_id}")
        self._attr_name = f"Sinum {self._room_name} Heating"
        self._attr_unique_id = f"{DOMAIN}_{room_id}_heating"
        self._attr_device_class = BinarySensorDeviceClass.HEAT

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        if self.coordinator.data and self._room_id in self.coordinator.data:
            room_data = self.coordinator.data[self._room_id]
            heating_on = room_data.get("heating_on", False)
            return bool(heating_on)
        return False

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            ATTR_ROOM_ID: self._room_id,
            ATTR_ROOM_NAME: self._room_name,
        }


class SinumCoolingBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Sinum cooling circuit binary sensor."""

    def __init__(
        self,
        coordinator: SinumDataUpdateCoordinator,
        room_id: str | int,
        room_data: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._room_id = room_id
        self._room_name = room_data.get("name", f"Room {room_id}")
        self._attr_name = f"Sinum {self._room_name} Cooling"
        self._attr_unique_id = f"{DOMAIN}_{room_id}_cooling"
        self._attr_device_class = BinarySensorDeviceClass.COLD

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        if self.coordinator.data and self._room_id in self.coordinator.data:
            room_data = self.coordinator.data[self._room_id]
            cooling_on = room_data.get("cooling_on", False)
            return bool(cooling_on)
        return False

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            ATTR_ROOM_ID: self._room_id,
            ATTR_ROOM_NAME: self._room_name,
        }

