from fastapi import WebSocket
from typing import Dict, Optional, Set


class ConnectionManager:
    """Manages active WebSocket connections per client ID."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections.setdefault(client_id, set()).add(websocket)

    def disconnect(self, client_id: str, websocket: Optional[WebSocket] = None):
        sockets = self.active_connections.get(client_id)
        if not sockets:
            return
        if websocket is None:
            self.active_connections.pop(client_id, None)
            return
        sockets.discard(websocket)
        if not sockets:
            self.active_connections.pop(client_id, None)

    async def send_message(self, message: dict, client_id: str):
        sockets = list(self.active_connections.get(client_id, ()))
        for websocket in sockets:
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(client_id, websocket)


manager = ConnectionManager()