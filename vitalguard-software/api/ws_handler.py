"""
WebSocket Handler
==================
Manages WebSocket connections for real-time dashboard updates.
Broadcasts digital twin state to all connected clients.
"""

import json
import asyncio
from typing import Set
from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected client."""
        self.active_connections.discard(websocket)

    async def broadcast(self, data: dict):
        """
        Send data to all connected clients.
        Automatically removes dead connections.
        """
        dead = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections.discard(ws)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)