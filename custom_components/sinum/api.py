"""API client for Sinum."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

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
            self._session = aiohttp.ClientSession()
        return self._session

    async def async_authenticate(self) -> None:
        """Authenticate with Sinum API."""
        session = await self._get_session()
        
        # TODO: Upravte túto časť podľa skutočného API Sinum
        # Toto je príklad implementácie - je potrebné upraviť podľa skutočného API
        auth_url = f"{self.host}/api/auth/login"
        
        try:
            async with session.post(
                auth_url,
                json={"username": self.username, "password": self.password},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._auth_token = data.get("token") or data.get("access_token")
                    if not self._auth_token:
                        raise Exception("No token received from API")
                else:
                    raise Exception(f"Authentication failed: {response.status}")
        except aiohttp.ClientError as err:
            raise Exception(f"Connection error: {err}") from err

    async def async_test_connection(self) -> None:
        """Test connection to Sinum API."""
        await self.async_authenticate()
        
        # Test získania dát
        await self.async_get_rooms()

    async def async_get_rooms(self) -> list[dict[str, Any]]:
        """Get list of rooms with temperatures."""
        if not self._auth_token:
            await self.async_authenticate()
        
        session = await self._get_session()
        
        # TODO: Upravte túto časť podľa skutočného API Sinum
        # Toto je príklad implementácie - je potrebné upraviť podľa skutočného API
        rooms_url = f"{self.host}/api/rooms"
        
        headers = {}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        
        try:
            async with session.get(
                rooms_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Očakávaný formát: [{"id": 1, "name": "Obývačka", "temperature": 22.5}, ...]
                    return data if isinstance(data, list) else data.get("rooms", [])
                else:
                    raise Exception(f"Failed to get rooms: {response.status}")
        except aiohttp.ClientError as err:
            raise Exception(f"Connection error: {err}") from err

    async def async_close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

