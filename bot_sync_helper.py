# Helper client for syncing bot state (VIP, points, servers) to the website APIs
# Usage: import this module inside your discord.py bot

import aiohttp
from typing import Optional

API_BASE = "https://www.skrew.ct.ws"
API_KEY = "skro_vip_api_key_change_me"  # TODO: change to a secret value in both bot and backend

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}

class WebsiteSyncClient:
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session

    def attach_session(self, session: aiohttp.ClientSession):
        self._session = session

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def set_vip(self, user_id: int, tier: Optional[str]):
        """Set VIP tier ("Diamond"|"Gold"|"Silver") or None to remove."""
        session = await self._ensure_session()
        url = f"{API_BASE}/api/vip/set"
        payload = {"user_id": user_id, "vip_tier": tier}
        async with session.post(url, json=payload, headers=HEADERS, timeout=15) as resp:
            data = await resp.json()
            if resp.status != 200 or not data.get("ok"):
                raise RuntimeError(f"VIP sync failed: {resp.status} - {data}")
            return data

    async def update_points(self, guild_id: int, user_id: int, *,
                            points: int = 0, wins: int = 0, games: int = 0,
                            score: Optional[int] = None, mode: str = "inc"):
        session = await self._ensure_session()
        url = f"{API_BASE}/api/points/update"
        payload = {
            "guild_id": guild_id,
            "user_id": user_id,
            "mode": mode,
            "points": points,
            "wins": wins,
            "games": games,
            "score": score,
        }
        async with session.post(url, json=payload, headers=HEADERS, timeout=15) as resp:
            data = await resp.json()
            if resp.status != 200 or not data.get("ok"):
                raise RuntimeError(f"Points sync failed: {resp.status} - {data}")
            return data

    async def set_servers(self, servers: int):
        session = await self._ensure_session()
        url = f"{API_BASE}/api/servers/set"
        payload = {"servers": servers}
        async with session.post(url, json=payload, headers=HEADERS, timeout=15) as resp:
            data = await resp.json()
            if resp.status != 200 or not data.get("ok"):
                raise RuntimeError(f"Servers sync failed: {resp.status} - {data}")
            return data

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
