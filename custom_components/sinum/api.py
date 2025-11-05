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
                        self._auth_token = (
                            data.get("token")
                            or data.get("access_token")
                            or data.get("accessToken")
                            or data.get("auth_token")
                            or data.get("access_token")
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
        
        According to Sinum API documentation:
        GET /rooms (or similar endpoint) with Authorization header
        Returns list of rooms with temperature data.
        """
        if not self._auth_token:
            await self.async_authenticate()
        
        session = await self._get_session()
        
        # Sinum API endpoint for rooms - try common variations
        # Based on API structure, likely /api/v1/rooms or similar
        possible_rooms_endpoints = [
            f"{self.host}/api/v1/rooms",  # Most likely based on login endpoint
            f"{self.host}/api/v1/rooms/temperatures",
            f"{self.host}/api/rooms",
            f"{self.host}/rooms",
        ]
        
        headers = {
            "Authorization": f"Bearer {self._auth_token}",
            "Content-Type": "application/json",
        }
        
        last_error = None
        
        for rooms_url in possible_rooms_endpoints:
            _LOGGER.debug("Trying rooms endpoint: %s", rooms_url)
            
            try:
                async with session.get(
                    rooms_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        _LOGGER.info("Successfully retrieved rooms from endpoint: %s", rooms_url)
                        # Handle different response formats
                        if isinstance(data, list):
                            # Direct list: [{"id": 1, "name": "Room", "temperature": 22.5}, ...]
                            return data
                        elif isinstance(data, dict):
                            # Wrapped in object: {"rooms": [...], "data": [...], etc.}
                            rooms_list = (
                                data.get("rooms", [])
                                or data.get("data", [])
                                or data.get("items", [])
                                or []
                            )
                            if rooms_list:
                                return rooms_list
                        else:
                            _LOGGER.warning("Unexpected response format: %s", type(data))
                    elif response.status == 401:
                        # Token expired, try to re-authenticate once
                        _LOGGER.warning("Token expired, re-authenticating...")
                        self._auth_token = None
                        await self.async_authenticate()
                        # Retry once with new token
                        headers["Authorization"] = f"Bearer {self._auth_token}"
                        async with session.get(
                            rooms_url,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as retry_response:
                            if retry_response.status == 200:
                                data = await retry_response.json()
                                if isinstance(data, list):
                                    return data
                                elif isinstance(data, dict):
                                    rooms_list = (
                                        data.get("rooms", [])
                                        or data.get("data", [])
                                        or data.get("items", [])
                                        or []
                                    )
                                    if rooms_list:
                                        return rooms_list
                            raise InvalidAuth("Authentication failed after retry")
                    elif response.status == 404:
                        # Endpoint not found, try next one
                        _LOGGER.debug("Endpoint %s not found (404), trying next...", rooms_url)
                        continue
                    else:
                        error_text = await response.text()
                        _LOGGER.warning("Failed to get rooms from %s: %s - %s", rooms_url, response.status, error_text[:200])
                        last_error = CannotConnect(f"Failed to get rooms: {response.status}")
                        continue
                        
            except (InvalidAuth, CannotConnect) as err:
                raise
            except aiohttp.ClientConnectorError as err:
                _LOGGER.debug("Connection error to %s: %s", rooms_url, err)
                last_error = CannotConnect(f"Cannot connect to Sinum API at {rooms_url}: {err}")
                continue
            except aiohttp.ClientError as err:
                _LOGGER.debug("HTTP error to %s: %s", rooms_url, err)
                last_error = CannotConnect(f"Connection error to {rooms_url}: {err}")
                continue
            except Exception as err:
                _LOGGER.debug("Unexpected error with %s: %s", rooms_url, err)
                last_error = CannotConnect(f"Error getting rooms: {err}")
                continue
        
        # If we get here, all endpoints failed
        if last_error:
            raise last_error
        else:
            raise CannotConnect("All rooms endpoints failed")

    async def async_close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

