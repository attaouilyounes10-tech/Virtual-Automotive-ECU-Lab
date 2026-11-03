"""Endpoint WebSocket `/ws/live` pour la diffusion en temps réel de la simulation."""

import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, WebSocket

from ..api.dependencies import get_simulation_engine
from ..websocket_manager import manager
from ..simulation.simulation import SimulationEngine

router = APIRouter()


@router.websocket("/ws/live")
async def websocket_endpoint(
    websocket: WebSocket,
    engine: SimulationEngine = Depends(get_simulation_engine)
):
    """Endpoint WebSocket `/ws/live`.

    Diffuse des données de simulation en temps réel à tous les clients connectés.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Diffuser toutes les500ms (2Hz) pour éviter la surcharge
            await asyncio.sleep(0.5)
            # Obtenir l'état actuel du moteur de simulation
            state = engine.get_simulation_state()
            # Construire le payload JSON
            payload = {
                "type": "telemetry",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "speed_kmh": state["vehicle_state"]["speed_kmh"],
                    "target_speed_kmh": state["vehicle_state"]["target_speed_kmh"],
                    "acceleration_mps2": state["vehicle_state"]["acceleration_mps2"],
                    "throttle_position_pct": state["vehicle_state"]["throttle_position_pct"],
                    "brake_pressure_bar": state["vehicle_state"]["brake_pressure_bar"],
                    "obstacle_detected": state["vehicle_state"]["obstacle_detected"],
                    "obstacle_distance_m": state["vehicle_state"]["obstacle_distance_m"],
                    "relative_speed_mps": state["vehicle_state"]["relative_speed_mps"],
                    "collision_risk_level": state["vehicle_state"]["collision_risk_level"],
                    "fcw_active": state["vehicle_state"]["fcw_active"],
                    "aeb_active": state["vehicle_state"]["aeb_active"],
                }
            }
            # Envoyer le payload à tous les clients connectés
            await manager.broadcast(payload)
    except Exception as e:
        # Retourner l'erreur sans l'exposer directement au client
        print(f"Exception WebSocket : {e}")
    finally:
        # Retirer la connexion
        manager.disconnect(websocket)