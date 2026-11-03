"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import dependencies
from backend.app.routers import simulation, health, websocket, ecu

app = FastAPI(
    title="Virtual Automotive CAN Simulation API",
    version="1.0.0",
    description="API for controlling and monitoring the Virtual Automotive CAN Simulation Engine",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add CORS middleware to allow frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(simulation.router, prefix="/api", tags=["simulation"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])
app.include_router(ecu.router, prefix="/api", tags=["ecus"])


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse(content={"message": "Virtual Automotive CAN Simulation API"})