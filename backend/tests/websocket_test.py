"""Tests de l'endpoint WebSocket `/api/ws/live` avec FastAPI TestClient."""

import json
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture(autouse=True)
def simulation_start():
    """Démarre la simulation avant chaque test et l'arrête après."""
    client = TestClient(app)
    client.post("/api/simulation/start")
    yield
    client.post("/api/simulation/stop")


def test_websocket_live_multiple_clients():
    """Test multiple clients WebSocket simultanément."""
    client1 = TestClient(app)
    client2 = TestClient(app)

    try:
        # Connexion WebSocket pour le client1 (avec /api/ws/live)
        with client1.websocket_connect("/api/ws/live") as ws1:
            # Connexion WebSocket pour le client2
            with client2.websocket_connect("/api/ws/live") as ws2:
                # Attendre que chaque client reçoive au moins un message
                data1 = json.loads(ws1.receive_text())
                data2 = json.loads(ws2.receive_text())

                # Vérifier la structure du message
                assert data1["type"] == "telemetry"
                assert "timestamp" in data1
                assert "data" in data1
                data_fields = set(data1["data"].keys())
                expected_fields = {
                    "speed_kmh", "target_speed_kmh", "acceleration_mps2",
                    "throttle_position_pct", "brake_pressure_bar",
                    "obstacle_detected", "obstacle_distance_m",
                    "relative_speed_mps", "collision_risk_level",
                    "fcw_active", "aeb_active"
                }
                assert expected_fields.issubset(data_fields)

                # Vérifier que les deux clients ont des vitesses cohérentes (0-120 km/h)
                speed1 = data1["data"]["speed_kmh"]
                speed2 = data2["data"]["speed_kmh"]
                assert 0.0 <= speed1 <= 120.0
                assert 0.0 <= speed2 <= 120.0
    finally:
        client1.post("/api/simulation/stop")
        client2.post("/api/simulation/stop")


def test_websocket_live_reconnect_after_disconnect():
    """Test de reconnectivité après déconnexion d'un client."""
    client = TestClient(app)

    try:
        # Connexion initiale
        with client.websocket_connect("/api/ws/live") as ws:
            data = json.loads(ws.receive_text())
            assert data["type"] == "telemetry"

        # Nouvelle connexion (reconnexion)
        with client.websocket_connect("/api/ws/live") as ws2:
            data = json.loads(ws2.receive_text())
            assert data["type"] == "telemetry"
    finally:
        client.post("/api/simulation/stop")


def test_websocket_live_message_frequency():
    """Test que l'endpoint WebSocket diffuse des messages à une fréquence approximative."""
    client = TestClient(app)

    try:
        client.post("/api/simulation/start")

        with client.websocket_connect("/api/ws/live") as ws:
            # Collecter les horodatages des 5 premiers messages
            timestamps = []
            for _ in range(5):
                data = json.loads(ws.receive_text())
                timestamps.append(data["timestamp"])

            # Calculer les intervalles (en secondes)
            intervals = []
            for i in range(1, len(timestamps)):
                t1 = datetime.fromisoformat(timestamps[i - 1])
                t2 = datetime.fromisoformat(timestamps[i])
                intervals.append((t2 - t1).total_seconds())

            # Les intervalles devraient être proches de 0,5s ±0,3s
            avg_interval = sum(intervals) / len(intervals) if intervals else 0.5
            assert 0.2 <= avg_interval <= 1.0, f"Intervalle moyen {avg_interval}s hors de la plage attendue"
    finally:
        client.post("/api/simulation/stop")


def test_websocket_live_error_handling():
    """Test que les erreurs WebSocket sont gérées gracieusement."""
    client = TestClient(app)

    try:
        # Connexion et déconnexion immédiate (simuler une déconnexion brutale)
        with client.websocket_connect("/api/ws/live") as ws:
            pass  # Fermer automatiquement à la sortie du bloc

        # Vérifier que l'API est toujours accessible (pas d'exception non gérée)
        response = client.get("/api/health")
        assert response.status_code == 200
    finally:
        client.post("/api/simulation/stop")


def test_websocket_live_simulation_state():
    """Test que les données WebSocket correspondent à l'état réel du moteur de simulation."""
    client = TestClient(app)

    try:
        client.post("/api/simulation/start")

        with client.websocket_connect("/api/ws/live") as ws:
            data = json.loads(ws.receive_text())
            ws_payload = data["data"]

            # Obtenir l'état actuel du moteur via l'API
            status_response = client.get("/api/status")
            assert status_response.status_code == 200
            sim_state = status_response.json()["vehicle_state"]

            # Comparer les données pertinentes
            for key in ws_payload:
                assert ws_payload[key] == sim_state[key], (
                    f"Mismatch pour {key}: WebSocket {ws_payload[key]} vs API {sim_state[key]}"
                )
    finally:
        client.post("/api/simulation/stop")