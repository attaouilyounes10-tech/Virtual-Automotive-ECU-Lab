"""Simulation control and monitoring router."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List

from ..api.dependencies import get_simulation_engine
from ..simulation.simulation import SimulationEngine

router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SimulationConfig(BaseModel):
    """Configuration model for simulation parameters."""
    target_speed_kmh: Optional[float] = Field(None, ge=0, le=300, description="Target vehicle speed in km/h")
    throttle_position_pct: Optional[float] = Field(None, ge=0, le=100, description="Throttle position percentage")
    obstacle_detected: Optional[bool] = Field(None, description="Whether an obstacle is detected")
    obstacle_distance_m: Optional[float] = Field(None, ge=0, le=1000, description="Distance to obstacle in meters")
    relative_speed_mps: Optional[float] = Field(None, ge=-100, le=100, description="Relative speed of obstacle in m/s")


class SimulationStatus(BaseModel):
    """Current simulation status model."""
    running: bool
    paused: bool
    current_time: float
    elapsed_time: float
    vehicle_state: dict


class CANFrameResponse(BaseModel):
    """CAN frame response model."""
    id: int
    data: str  # hex string
    dlc: int
    is_rtr: bool
    timestamp: float


class CANFramesResponse(BaseModel):
    """Response model for CAN frames list."""
    frames: List[CANFrameResponse]
    total: int


class SimulationControlResponse(BaseModel):
    """Response model for simulation control operations."""
    success: bool
    message: str
    state: Optional[SimulationStatus] = None


class TelemetryResponse(BaseModel):
    """Telemetry data response."""
    speed_kmh: float
    target_speed_kmh: float
    acceleration_mps2: float
    throttle_position_pct: float
    brake_pressure_bar: float
    obstacle_detected: bool
    obstacle_distance_m: float
    relative_speed_mps: float
    collision_risk_level: int
    fcw_active: bool
    aeb_active: bool


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_engine_state(engine: SimulationEngine) -> SimulationStatus:
    """Get formatted engine state."""
    state = engine.get_simulation_state()
    return SimulationStatus(
        running=state['is_running'],
        paused=state['is_paused'],
        current_time=state['current_time'],
        elapsed_time=state['elapsed_time'],
        vehicle_state=state['vehicle_state']
    )


def frame_to_response(frame) -> CANFrameResponse:
    """Convert CAN frame to response model."""
    return CANFrameResponse(
        id=frame.id,
        data=frame.data.hex(),
        dlc=frame.dlc,
        is_rtr=frame.is_rtr,
        timestamp=frame.timestamp
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/status", response_model=SimulationStatus, tags=["simulation"])
async def get_simulation_status(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Get the current simulation status including engine state and vehicle telemetry.
    """
    return get_engine_state(engine)


@router.get("/telemetry", response_model=TelemetryResponse, tags=["simulation"])
async def get_telemetry(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Get current vehicle telemetry data.
    Returns key vehicle parameters including speed, acceleration, and ADAS status.
    """
    state = engine.get_simulation_state()
    vs = state['vehicle_state']
    return TelemetryResponse(
        speed_kmh=vs['speed_kmh'],
        target_speed_kmh=vs['target_speed_kmh'],
        acceleration_mps2=vs['acceleration_mps2'],
        throttle_position_pct=vs['throttle_position_pct'],
        brake_pressure_bar=vs['brake_pressure_bar'],
        obstacle_detected=vs['obstacle_detected'],
        obstacle_distance_m=vs['obstacle_distance_m'],
        relative_speed_mps=vs['relative_speed_mps'],
        collision_risk_level=vs['collision_risk_level'],
        fcw_active=vs['fcw_active'],
        aeb_active=vs['aeb_active']
    )


@router.get("/can/frames", response_model=CANFramesResponse, tags=["simulation"])
async def get_can_frames(
    limit: int = 100,
    engine: SimulationEngine = Depends(get_simulation_engine)
):
    """
    Get recent CAN frames from the bus.
    """
    history = engine.bus.get_message_history()
    # Get the last 'limit' frames
    frames = history[-limit:] if limit > 0 else history

    return CANFramesResponse(
        frames=[frame_to_response(f) for f in frames],
        total=len(history)
    )


@router.post("/simulation/start", response_model=SimulationControlResponse, tags=["simulation"])
async def start_simulation(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Start the simulation engine.
    """
    if engine.is_running:
        return SimulationControlResponse(
            success=False,
            message="Simulation is already running",
            state=get_engine_state(engine)
        )

    engine.start()
    return SimulationControlResponse(
        success=True,
        message="Simulation started successfully",
        state=get_engine_state(engine)
    )


@router.post("/simulation/stop", response_model=SimulationControlResponse, tags=["simulation"])
async def stop_simulation(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Stop the simulation engine.
    """
    if not engine.is_running:
        return SimulationControlResponse(
            success=False,
            message="Simulation is not running",
            state=get_engine_state(engine)
        )

    engine.stop()
    return SimulationControlResponse(
        success=True,
        message="Simulation stopped successfully",
        state=get_engine_state(engine)
    )


@router.post("/simulation/pause", response_model=SimulationControlResponse, tags=["simulation"])
async def pause_simulation(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Pause the simulation engine.
    """
    if not engine.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot pause: simulation is not running"
        )

    if engine.is_paused:
        return SimulationControlResponse(
            success=False,
            message="Simulation is already paused",
            state=get_engine_state(engine)
        )

    engine.pause()
    return SimulationControlResponse(
        success=True,
        message="Simulation paused successfully",
        state=get_engine_state(engine)
    )


@router.post("/simulation/resume", response_model=SimulationControlResponse, tags=["simulation"])
async def resume_simulation(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Resume the simulation engine from paused state.
    """
    if not engine.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resume: simulation is not running"
        )

    if not engine.is_paused:
        return SimulationControlResponse(
            success=False,
            message="Simulation is not paused",
            state=get_engine_state(engine)
        )

    engine.resume()
    return SimulationControlResponse(
        success=True,
        message="Simulation resumed successfully",
        state=get_engine_state(engine)
    )


@router.post("/simulation/reset", response_model=SimulationControlResponse, tags=["simulation"])
async def reset_simulation(engine: SimulationEngine = Depends(get_simulation_engine)):
    """
    Reset the simulation to initial state.
    """
    if engine.is_running:
        engine.reset()
    else:
        engine.start()

    return SimulationControlResponse(
        success=True,
        message="Simulation reset successfully",
        state=get_engine_state(engine)
    )


@router.post("/simulation/config", response_model=SimulationControlResponse, tags=["simulation"])
async def configure_simulation(
    config: SimulationConfig,
    engine: SimulationEngine = Depends(get_simulation_engine)
):
    """
    Configure simulation parameters.
    """
    updated = []
    vs = engine.vehicle_state

    if config.target_speed_kmh is not None:
        vs['target_speed_kmh'] = config.target_speed_kmh
        updated.append(f"target_speed_kmh={config.target_speed_kmh}")

    if config.throttle_position_pct is not None:
        vs['throttle_position_pct'] = config.throttle_position_pct
        updated.append(f"throttle_position_pct={config.throttle_position_pct}")

    if config.obstacle_detected is not None:
        vs['obstacle_detected'] = config.obstacle_detected
        updated.append(f"obstacle_detected={config.obstacle_detected}")

    if config.obstacle_distance_m is not None:
        vs['obstacle_distance_m'] = config.obstacle_distance_m
        updated.append(f"obstacle_distance_m={config.obstacle_distance_m}")

    if config.relative_speed_mps is not None:
        vs['relative_speed_mps'] = config.relative_speed_mps
        updated.append(f"relative_speed_mps={config.relative_speed_mps}")

    message = f"Configuration updated: {', '.join(updated)}" if updated else "No configuration changes"

    return SimulationControlResponse(
        success=True,
        message=message,
        state=get_engine_state(engine)
    )