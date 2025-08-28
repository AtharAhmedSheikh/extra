from fastapi import WebSocket
from typing import Dict, List
from pydantic import BaseModel

class ConnectionManager:
    def __init__(self):
        # phone_number -> list of WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, phone_number: str, websocket: WebSocket):
        await websocket.accept()
        if phone_number not in self.active_connections:
            self.active_connections[phone_number] = []
        self.active_connections[phone_number].append(websocket)

    def disconnect(self, phone_number: str, websocket: WebSocket):
        if phone_number in self.active_connections:
            self.active_connections[phone_number].remove(websocket)
            if not self.active_connections[phone_number]:
                del self.active_connections[phone_number]

    async def send_to_phone(self, phone_number: str, data: BaseModel):
        """Send data only to connections for a specific phone number."""
        json_str = data.model_dump_json()
        if phone_number in self.active_connections:
            for connection in self.active_connections[phone_number]:
                await connection.send_text(json_str)

    async def send_to_all(self, data: BaseModel):
        """Broadcast to all connected clients (optional)."""
        json_str = data.model_dump_json()
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_text(json_str)

websocket_manager = ConnectionManager()
