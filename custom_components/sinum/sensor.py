"""Sensor platform for Sinum integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    """Set up Sinum sensor platform."""
    api = hass.data[DOMAIN][entry.entry_id]
    coordinator = SinumDataUpdateCoordinator(hass, api)
    
    # Fetch initial data so we have data to create entities
    await coordinator.async_config_entry_first_refresh()
    
    async_add_entities(
        SinumTemperatureSensor(coordinator, room_id, room_data)
        for room_id, room_data in coordinator.data.items()
    )


class SinumTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sinum temperature sensor."""

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
        self._attr_name = f"Sinum {self._room_name}"
        self._attr_unique_id = f"{DOMAIN}_{room_id}_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data and self._room_id in self.coordinator.data:
            room_data = self.coordinator.data[self._room_id]
            temperature = room_data.get("temperature")
            if temperature is not None:
                try:
                    return float(temperature)
                except (ValueError, TypeError):
                    return None
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            ATTR_ROOM_ID: self._room_id,
            ATTR_ROOM_NAME: self._room_name,
        }

