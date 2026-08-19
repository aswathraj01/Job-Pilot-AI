"""
WebSocket connection manager for real-time job processing status updates.
Clients connect to /ws/jobs/{job_id}?token=<jwt> and receive status updates.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per job ID."""

    def __init__(self) -> None:
        # Maps job_id (str) → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        await websocket.accept()
        self._connections[job_id].append(websocket)
        logger.info("ws_connected", job_id=job_id)

    def disconnect(self, websocket: WebSocket, job_id: str) -> None:
        conns = self._connections.get(job_id, [])
        if websocket in conns:
            conns.remove(websocket)
        logger.info("ws_disconnected", job_id=job_id)

    async def broadcast_status(
        self,
        job_id: str,
        status: str,
        message: str | None = None,
        progress: int = 0,
        extra: dict | None = None,
    ) -> None:
        """Push a status update to all subscribers of a job_id."""
        payload = {
            "job_id": job_id,
            "status": status,
            "message": message,
            "progress": progress,
            **(extra or {}),
        }
        data = json.dumps(payload)
        dead: list[WebSocket] = []
        for ws in self._connections.get(job_id, []):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, job_id)

    async def send_personal(self, websocket: WebSocket, data: dict) -> None:
        await websocket.send_text(json.dumps(data))


# Singleton instance shared across the app
ws_manager = ConnectionManager()
