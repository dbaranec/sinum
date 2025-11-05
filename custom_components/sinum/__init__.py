"""The Sinum integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import SinumAPI
from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sinum from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create API instance
    api = SinumAPI(
        host=entry.data["host"],
        username=entry.data["username"],
        password=entry.data["password"],
    )
    
    # Test connection
    try:
        await api.async_test_connection()
    except Exception as err:
        raise Exception(f"Failed to connect to Sinum: {err}") from err
    
    # Store API instance
    hass.data[DOMAIN][entry.entry_id] = api
    
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

