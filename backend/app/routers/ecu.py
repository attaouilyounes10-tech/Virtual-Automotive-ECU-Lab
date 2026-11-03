"""ECU status router — exposes per-ECU state via REST."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional

from ..api.dependencies import get_simulation_engine
from ..simulation.simulation import SimulationEngine

router = APIRouter()


class ECUStatusResponse(BaseModel):
    """Status summary for one ECU."""
    id: str
    type: str
    active: bool
    connected: bool
    last_message_time: float
    message_count: int
    extra: dict


class AllECUStatusResponse(BaseModel):
    ecus: List[ECUStatusResponse]


@router.get("/ecus/status", response_model=AllECUStatusResponse, tags=["ecus"])
async def get_all_ecu_status(engine: SimulationEngine = Depends(get_simulation_engine)):
    """Return the current status of all three ECUs (ADAS, VCU, Dashboard)."""
    adas = engine.adas.get_status()
    vcu = engine.vcu.get_status()
    dash = engine.dash.get_status()

    def _to_response(raw: dict) -> ECUStatusResponse:
        return ECUStatusResponse(
            id=raw["id"],
            type=raw["type"],
            active=raw["active"],
            connected=raw["connected"],
            last_message_time=raw["last_message_time"],
            message_count=raw["message_count"],
            extra={k: v for k, v in raw.items() if k not in
                  ("id", "type", "active", "connected", "last_message_time", "message_count")},
        )

    return AllECUStatusResponse(ecus=[_to_response(adas), _to_response(vcu), _to_response(dash)])


@router.get("/ecus/can/messages", tags=["ecus"])
async def get_dbc_messages(engine: SimulationEngine = Depends(get_simulation_engine)):
    """Return all CAN message definitions from the DBC file."""
    return {"messages": engine.dbc_loader.list_all_messages()}
