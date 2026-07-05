import asyncio
from datetime import datetime
from typing import Any

from fastapi import WebSocket


class SyncProgressHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._latest: dict[str, Any] = {
            "stage": "idle",
            "message": "等待同步",
            "provider": None,
            "code": None,
            "percent": 0,
            "current": 0,
            "total": 0,
            "updated_at": datetime.now().isoformat(),
        }

    @property
    def latest(self) -> dict[str, Any]:
        return self._latest

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        await websocket.send_json(self._latest)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def publish(
        self,
        stage: str,
        message: str,
        *,
        provider: str | None = None,
        code: str | None = None,
        percent: int | None = None,
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        self._latest = {
            "stage": stage,
            "message": message,
            "provider": provider,
            "code": code,
            "percent": percent if percent is not None else self._latest.get("percent", 0),
            "current": current if current is not None else self._latest.get("current", 0),
            "total": total if total is not None else self._latest.get("total", 0),
            "updated_at": datetime.now().isoformat(),
        }
        if not self._connections:
            return
        await asyncio.gather(
            *[self._safe_send(connection, self._latest) for connection in list(self._connections)]
        )

    async def _safe_send(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        try:
            await websocket.send_json(payload)
        except RuntimeError:
            self.disconnect(websocket)


progress_hub = SyncProgressHub()
