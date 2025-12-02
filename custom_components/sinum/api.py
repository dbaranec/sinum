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
        self._token_expires_at: float | None = None  # Timestamp when token expires

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
                            # Parse token expiration time from JWT payload
                            try:
                                import base64
                                import json as json_lib
                                import time
                                
                                # Decode JWT token to get expiration
                                token_parts = self._auth_token.split(".")
                                if len(token_parts) >= 2:
                                    # Decode payload (add padding if needed)
                                    payload_b64 = token_parts[1]
                                    padding = 4 - len(payload_b64) % 4
                                    if padding != 4:
                                        payload_b64 += "=" * padding
                                    
                                    payload = json_lib.loads(
                                        base64.urlsafe_b64decode(payload_b64).decode()
                                    )
                                    
                                    # Get expiration time
                                    expires_at = payload.get("expires_at")
                                    expires_in = payload.get("expires_in", 3600)
                                    
                                    if expires_at:
                                        # expires_at is Unix timestamp
                                        # Set expiration 5 minutes before actual expiration for safety
                                        self._token_expires_at = expires_at - 300
                                    elif expires_in:
                                        # expires_in is seconds until expiration
                                        self._token_expires_at = time.time() + expires_in - 300
                                    else:
                                        # Default: assume 1 hour expiration, refresh after 55 minutes
                                        self._token_expires_at = time.time() + 3300
                                    
                                    _LOGGER.debug("Token expires at: %s", self._token_expires_at)
                            except Exception as err:
                                _LOGGER.debug("Could not parse token expiration: %s", err)
                                # Default: assume 1 hour expiration, refresh after 55 minutes
                                import time
                                self._token_expires_at = time.time() + 3300
                            
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

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid authentication token."""
        import time
        
        # Check if token is expired or about to expire
        if self._auth_token and self._token_expires_at:
            if time.time() >= self._token_expires_at:
                _LOGGER.info("Token expired, re-authenticating...")
                self._auth_token = None
                self._token_expires_at = None
        
        if not self._auth_token:
            await self.async_authenticate()

    async def async_get_rooms(self) -> list[dict[str, Any]]:
        """Get list of rooms with temperatures.
        
        Sinum API structure:
        - GET /api/v1/rooms returns rooms list
        - GET /api/v1/devices?class=sbus returns temperature sensors
        - Temperature sensors have room_id and temperature field
        """
        await self._ensure_authenticated()
        
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
                if response.status == 401:
                    # Token expired, re-authenticate and retry once
                    _LOGGER.warning("Token expired (401), re-authenticating...")
                    self._auth_token = None
                    self._token_expires_at = None
                    await self.async_authenticate()
                    headers["Authorization"] = self._auth_token
                    # Retry once
                    async with session.get(
                        rooms_url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as retry_response:
                        if retry_response.status != 200:
                            error_text = await retry_response.text()
                            raise InvalidAuth(f"Authentication failed after retry: {retry_response.status} - {error_text[:200]}")
                        rooms_data = await retry_response.json()
                elif response.status != 200:
                    error_text = await response.text()
                    raise CannotConnect(f"Failed to get rooms: {response.status} - {error_text[:200]}")
                else:
                    rooms_data = await response.json()
                
            rooms_list = rooms_data.get("data", []) if isinstance(rooms_data, dict) else (rooms_data if isinstance(rooms_data, list) else [])
            
            # Get sbus devices (temperature and humidity sensors)
            devices_url = f"{self.host}/api/v1/devices?class=sbus"
            async with session.get(
                devices_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    # Token expired, re-authenticate and retry once
                    _LOGGER.warning("Token expired (401) when getting devices, re-authenticating...")
                    self._auth_token = None
                    self._token_expires_at = None
                    await self.async_authenticate()
                    headers["Authorization"] = self._auth_token
                    # Retry once
                    async with session.get(
                        devices_url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as retry_response:
                        if retry_response.status != 200:
                            error_text = await retry_response.text()
                            _LOGGER.warning("Failed to get devices after retry: %s - %s", retry_response.status, error_text[:200])
                            sbus_devices = []
                        else:
                            devices_data = await retry_response.json()
                            devices_dict = devices_data.get("data", {}) if isinstance(devices_data, dict) else {}
                            sbus_devices = devices_dict.get("sbus", []) if isinstance(devices_dict, dict) else []
                elif response.status != 200:
                    error_text = await response.text()
                    _LOGGER.warning("Failed to get devices: %s - %s", response.status, error_text[:200])
                    sbus_devices = []
                else:
                    devices_data = await response.json()
                    devices_dict = devices_data.get("data", {}) if isinstance(devices_data, dict) else {}
                    sbus_devices = devices_dict.get("sbus", []) if isinstance(devices_dict, dict) else []
            
            # Get virtual devices (thermostats with heating/cooling state)
            virtual_devices_url = f"{self.host}/api/v1/devices?class=virtual"
            async with session.get(
                virtual_devices_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    # Token expired, re-authenticate and retry once
                    _LOGGER.warning("Token expired (401) when getting virtual devices, re-authenticating...")
                    self._auth_token = None
                    self._token_expires_at = None
                    await self.async_authenticate()
                    headers["Authorization"] = self._auth_token
                    # Retry once
                    async with session.get(
                        virtual_devices_url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as retry_response:
                        if retry_response.status != 200:
                            error_text = await retry_response.text()
                            _LOGGER.warning("Failed to get virtual devices after retry: %s - %s", retry_response.status, error_text[:200])
                            virtual_devices = []
                        else:
                            devices_data = await retry_response.json()
                            devices_dict = devices_data.get("data", {}) if isinstance(devices_data, dict) else {}
                            virtual_devices = devices_dict.get("virtual", []) if isinstance(devices_dict, dict) else []
                elif response.status != 200:
                    error_text = await response.text()
                    _LOGGER.warning("Failed to get virtual devices: %s - %s", response.status, error_text[:200])
                    virtual_devices = []
                else:
                    devices_data = await response.json()
                    devices_dict = devices_data.get("data", {}) if isinstance(devices_data, dict) else {}
                    virtual_devices = devices_dict.get("virtual", []) if isinstance(devices_dict, dict) else []
            
            # Filter temperature and humidity sensors
            temp_sensors = [
                d for d in sbus_devices
                if d.get("type") == "temperature_sensor" and d.get("temperature") is not None
            ]
            humidity_sensors = [
                d for d in sbus_devices
                if d.get("type") == "humidity_sensor" and d.get("humidity") is not None
            ]
            
            # Create maps by room_id
            temp_by_room: dict[int, float] = {}
            humidity_by_room: dict[int, float] = {}
            heating_state_by_room: dict[int, bool] = {}
            cooling_state_by_room: dict[int, bool] = {}
            
            for sensor in temp_sensors:
                room_id = sensor.get("room_id")
                temp_tenths = sensor.get("temperature")
                if room_id and temp_tenths is not None:
                    # Convert from tenths of degrees to degrees (e.g., 223 -> 22.3)
                    temp_by_room[room_id] = temp_tenths / 10.0
            
            for sensor in humidity_sensors:
                room_id = sensor.get("room_id")
                humidity_tenths = sensor.get("humidity")
                if room_id and humidity_tenths is not None:
                    # Convert from tenths of percent to percent (e.g., 381 -> 38.1)
                    humidity_by_room[room_id] = humidity_tenths / 10.0
            
            for device in virtual_devices:
                room_id = device.get("room_id")
                if room_id:
                    # State indicates if heating/cooling circuit is active
                    # Mode indicates which type: "heating" or "cooling"
                    state = device.get("state", False)
                    mode = device.get("mode", "")
                    
                    # Initialize both to False
                    heating_state_by_room[room_id] = False
                    cooling_state_by_room[room_id] = False
                    
                    # If state is True, determine which mode is active
                    if state is True:
                        if mode == "heating":
                            heating_state_by_room[room_id] = True
                        elif mode == "cooling":
                            cooling_state_by_room[room_id] = True
                        # If state is True but mode is unclear, check is_heating/is_cooling
                        else:
                            is_heating = device.get("is_heating")
                            is_cooling = device.get("is_cooling")
                            if is_heating is True:
                                heating_state_by_room[room_id] = True
                            elif is_cooling is True:
                                cooling_state_by_room[room_id] = True
            
            # Combine rooms with all data
            result = []
            for room in rooms_list:
                room_id = room.get("id")
                room_name = room.get("name", f"Room {room_id}")
                
                result.append({
                    "id": room_id,
                    "name": room_name,
                    "temperature": temp_by_room.get(room_id) if room_id else None,
                    "humidity": humidity_by_room.get(room_id) if room_id else None,
                    "heating_on": heating_state_by_room.get(room_id, False) if room_id else False,
                    "cooling_on": cooling_state_by_room.get(room_id, False) if room_id else False,
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

