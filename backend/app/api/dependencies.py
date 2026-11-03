"""API dependencies for FastAPI - SimulationEngine singleton management."""

from typing import Optional
from fastapi import Depends, HTTPException

# Global simulation engine instance
_simulation_engine: Optional["SimulationEngine"] = None


def get_simulation_engine() -> "SimulationEngine":
    """Get or create the singleton SimulationEngine instance."""
    global _simulation_engine
    if _simulation_engine is None:
        from backend.app.simulation.simulation import SimulationEngine
        _simulation_engine = SimulationEngine(
            bus_name="api_simulation_bus",
            adas_id="adas_001",
            vcu_id="vcu_001",
            dash_id="dash_001"
        )
    return _simulation_engine


def reset_simulation_engine() -> None:
    """Reset the simulation engine instance (for testing)."""
    global _simulation_engine
    if _simulation_engine and _simulation_engine.is_running:
        _simulation_engine.stop()
    _simulation_engine = None