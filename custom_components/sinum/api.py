"""API client for Sinum."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)


class SinumAPI:
    """API client for Sinum."""

    def __init__(self, host: str, username: str, password: str) -> None:
        """Initialize the API client."""
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self._session: aiohttp.ClientSession | None = None
        self._auth_token: str | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            # Create SSL context that allows self-signed certificates
            # This is needed for local Sinum installations
            ssl_context = False  # Will disable SSL verification for local dev
            # For production, you might want to use: ssl_context = ssl.create_default_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def async_authenticate(self) -> None:
        """Authenticate with Sinum API.
        
        According to Sinum API documentation:
        POST /auth/login with username and password
        Returns token in response.
        """
        session = await self._get_session()
        
        # Try different possible endpoints (starting with correct one)
        possible_endpoints = [
            f"{self.host}/api/v1/login",  # Correct endpoint according to API docs
            f"{self.host}/auth/login",
            f"{self.host}/api/auth/login",
            f"{self.host}/login",
        ]
        
        last_error = None
        
        for auth_url in possible_endpoints:
            _LOGGER.debug("Trying authentication endpoint: %s", auth_url)
            
            try:
                # Try JSON first
                async with session.post(
                    auth_url,
                    json={"username": self.username, "password": self.password},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    response_text = await response.text()
                    _LOGGER.debug("Response status: %s, body: %s", response.status, response_text[:200])
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                        except Exception:
                            # If response is not JSON, try to parse as text
                            data = {"token": response_text.strip() if response_text.strip() else None}
                        
                        # Try different possible token field names
                        # Sinum API returns token in data.session
                        data_obj = data.get("data", {}) if isinstance(data.get("data"), dict) else {}
                        self._auth_token = (
                            data_obj.get("session")  # Sinum API format: data.session
                            or data_obj.get("access_token")
                            or data.get("token")
                            or data.get("access_token")
                            or data.get("accessToken")
                            or data.get("auth_token")
                        )
                        
                        if self._auth_token:
                            _LOGGER.info("Successfully authenticated with endpoint: %s", auth_url)
                            return
                        else:
                            _LOGGER.warning("No token in response from %s: %s", auth_url, data)
                            last_error = InvalidAuth(f"No token in response: {response_text[:100]}")
                    elif response.status == 401:
                        _LOGGER.error("Invalid credentials for endpoint %s: %s", auth_url, response_text[:200])
                        raise InvalidAuth("Invalid credentials - check username and password")
                    elif response.status == 404:
                        # Endpoint not found, try next one
                        _LOGGER.debug("Endpoint %s not found (404), trying next...", auth_url)
                        continue
                    else:
                        _LOGGER.warning("Unexpected status %s from %s: %s", response.status, auth_url, response_text[:200])
                        last_error = InvalidAuth(f"Authentication failed: {response.status} - {response_text[:100]}")
                        
            except aiohttp.ClientConnectorError as err:
                _LOGGER.debug("Connection error to %s: %s", auth_url, err)
                last_error = CannotConnect(f"Cannot connect to Sinum API at {auth_url}: {err}")
                continue
            except aiohttp.ClientError as err:
                _LOGGER.debug("HTTP error to %s: %s", auth_url, err)
                last_error = CannotConnect(f"Connection error to {auth_url}: {err}")
                continue
            except InvalidAuth:
                # Re-raise InvalidAuth immediately
                raise
            except Exception as err:
                _LOGGER.debug("Unexpected error with %s: %s", auth_url, err)
                last_error = InvalidAuth(f"Authentication error: {err}")
                continue
        
        # If we get here, all endpoints failed
        if last_error:
            raise last_error
        else:
            raise InvalidAuth("All authentication endpoints failed - check API URL and credentials")

    async def async_test_connection(self) -> None:
        """Test connection to Sinum API."""
        await self.async_authenticate()
        
        # Test získania dát
        await self.async_get_rooms()

    async def async_get_rooms(self) -> list[dict[str, Any]]:
        """Get list of rooms with temperatures.
        
        Sinum API structure:
        - GET /api/v1/rooms returns rooms list
        - GET /api/v1/devices?class=sbus returns temperature sensors
        - Temperature sensors have room_id and temperature field
        """
        if not self._auth_token:
            await self.async_authenticate()
        
        session = await self._get_session()
        
        headers = {
            "Authorization": self._auth_token,  # Sinum API uses token directly, not "Bearer {token}"
            "Content-Type": "application/json",
        }
        
        try:
            # Get rooms
            rooms_url = f"{self.host}/api/v1/rooms"
            _LOGGER.debug("Trying rooms endpoint: %s", rooms_url)
            
            async with session.get(
                rooms_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise CannotConnect(f"Failed to get rooms: {response.status} - {error_text[:200]}")
                
                rooms_data = await response.json()
                rooms_list = rooms_data.get("data", []) if isinstance(rooms_data, dict) else (rooms_data if isinstance(rooms_data, list) else [])
            
            # Get temperature sensors
            devices_url = f"{self.host}/api/v1/devices?class=sbus"
            async with session.get(
                devices_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.warning("Failed to get devices: %s - %s", response.status, error_text[:200])
                    # Continue without temperatures if devices endpoint fails
                    temp_sensors = []
                else:
                    devices_data = await response.json()
                    devices_dict = devices_data.get("data", {}) if isinstance(devices_data, dict) else {}
                    sbus_devices = devices_dict.get("sbus", []) if isinstance(devices_dict, dict) else []
                    # Filter temperature sensors
                    temp_sensors = [
                        d for d in sbus_devices
                        if d.get("type") == "temperature_sensor" and d.get("temperature") is not None
                    ]
            
            # Create temperature map by room_id
            temp_by_room: dict[int, float] = {}
            for sensor in temp_sensors:
                room_id = sensor.get("room_id")
                temp_tenths = sensor.get("temperature")
                if room_id and temp_tenths is not None:
                    # Convert from tenths of degrees to degrees (e.g., 223 -> 22.3)
                    temp_by_room[room_id] = temp_tenths / 10.0
            
            # Combine rooms with temperatures
            result = []
            for room in rooms_list:
                room_id = room.get("id")
                room_name = room.get("name", f"Room {room_id}")
                temperature = temp_by_room.get(room_id) if room_id else None
                
                result.append({
                    "id": room_id,
                    "name": room_name,
                    "temperature": temperature,
                })
            
            _LOGGER.info("Retrieved %d rooms with temperatures", len(result))
            return result
            
        except (InvalidAuth, CannotConnect):
            raise
        except aiohttp.ClientConnectorError as err:
            _LOGGER.error("Connection error: %s", err)
            raise CannotConnect(f"Cannot connect to Sinum API: {err}") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error: %s", err)
            raise CannotConnect(f"Connection error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise CannotConnect(f"Error getting rooms: {err}") from err

    async def async_close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

