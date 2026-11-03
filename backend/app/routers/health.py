"""Health check router."""

from fastapi import APIRouter, Depends

from ..api.dependencies import get_simulation_engine
from ..simulation.simulation import SimulationEngine

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Health check endpoint.
    Returns the status of the API and the simulation engine.
    """
    return {
        "status": "ok",
        "service": "Virtual Automotive CAN Simulation API",
        "version": "1.0.0",
        "simulation": {
            "running": engine.is_running,
            "paused": engine.is_paused,
        }
    }


@router.get("/health/detailed", tags=["health"])
async def health_detailed(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Detailed health check with simulation state.
    """
    state = engine.get_simulation_state()
    return {
        "status": "ok",
        "service": "Virtual Automotive CAN Simulation API",
        "version": "1.0.0",
        "simulation": state
    }