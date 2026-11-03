"""Gestionnaire de connexions WebSocket."""

from typing import Set
from fastapi import WebSocket


class ConnectionManager:
    """Gestionnaire de connexions WebSocket actives."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accepte la connexion WebSocket et l'ajoute au gestionnaire."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Retire la connexion du gestionnaire."""
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Diffuse le message JSON à tous les clients connectés."""
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)

    def connection_count(self) -> int:
        """Retourne le nombre de connexions actives."""
        return len(self.active_connections)


# Instance globale du gestionnaire
manager = ConnectionManager()