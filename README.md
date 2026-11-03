# 🚗 Virtual Automotive ECU Lab (VAEC)

A full-stack simulation platform that models a real-world **CAN (Controller Area Network) bus** entirely in software — no physical hardware required.

Built to demonstrate the interaction between embedded automotive ECUs (ADAS, VCU, Dashboard) in a virtual environment, with a modern React dashboard for live telemetry monitoring.

---

## ✨ Features

- **Virtual CAN Bus** — software pub/sub bus with 1000-frame history, thread-safe, DBC-encoded
- **Three simulated ECUs**
  - **ADAS_ECU** — obstacle detection, FCW (Forward Collision Warning), AEB (Autonomous Emergency Braking)
  - **VCU** — vehicle speed/acceleration/braking physics
  - **Dashboard_ECU** — alert aggregation and display
- **DBC support** — signal encoding/decoding via `cantools` and `vael_can.dbc`
- **Real-time WebSocket streaming** — 2 Hz telemetry broadcast to all connected clients
- **FastAPI REST API** — full simulation lifecycle control + telemetry endpoints
- **React dashboard** — live charts, CAN frame analyzer, ECU monitoring, diagnostics

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  React Frontend                  │
│  Overview · Vehicle Sim · ECU Monitor            │
│  CAN Analyzer · Diagnostics · Test Validation    │
└─────────────┬──────────────┬───────────────────┘
              │ REST /api/*  │ WS /api/ws/live
┌─────────────▼──────────────▼───────────────────┐
│                FastAPI Backend                   │
│  /api/health  /api/status  /api/telemetry        │
│  /api/simulation/*  /api/can/frames              │
│  /api/ecus/status   /api/ecus/can/messages       │
└─────────────────────────┬───────────────────────┘
                          │
┌─────────────────────────▼───────────────────────┐
│             SimulationEngine (thread)            │
│   vehicle_state · obstacle scenario · 50Hz loop  │
└──────┬──────────────┬──────────────┬────────────┘
       │              │              │
   ADAS_ECU        VCU_Ecu     Dashboard_Ecu
       └──────────────┴──────────────┘
                      │
              CANBus (pub/sub)
                      │
              vael_can.dbc (cantools)
```

---

## 📡 CAN Messages (vael_can.dbc)

| CAN ID | Name | Sender | Key Signals |
|--------|------|--------|-------------|
| 0x100 | ADAS_STATUS | ADAS_ECU | Obstacle_Distance_m, Collision_Risk_Level, FCW_Active, AEB_Active |
| 0x101 | COLLISION_WARNING | ADAS_ECU | Warning_Level, Time_To_Collision_s |
| 0x200 | VEHICLE_STATUS | VCU | Vehicle_Speed_kmh, Acceleration_mps2, Brake_Pressure_Bar |
| 0x201 | BRAKE_COMMAND | ADAS→VCU | Brake_Request, Brake_Force_N |
| 0x300 | DASHBOARD_ALERT | Dashboard_ECU | Alert_Type, Alert_Level |
| 0x700 | SYSTEM_DIAGNOSTICS | Diagnostic_ECU | ECU_ID, Error_Code |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm 9+

### 1. Backend

```powershell
# From project root — create and activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies (includes cantools)
pip install -r requirements.txt

# Start backend
.\scripts\start_backend.ps1
# OR directly:
uvicorn backend.app.main:app --reload --port 8000
```

Backend runs at **http://localhost:8000**  
Swagger UI: **http://localhost:8000/api/docs**

### 2. Frontend

```powershell
# In a new terminal
.\scripts\start_frontend.ps1
# OR directly:
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

### 3. Run Tests

```powershell
.\scripts\run_tests.ps1
# OR directly:
pytest backend/tests/ -v
```

---

## 📁 Project Structure

```
Virtual-Automotive-ECU-Lab/
├── backend/
│   ├── app/
│   │   ├── canbus/          # CAN bus core (CANBus, CANFrame, DBC loader, filters)
│   │   ├── ecus/            # ECU models (ADAS, VCU, Dashboard)
│   │   ├── simulation/      # SimulationEngine orchestrator
│   │   ├── routers/         # FastAPI routes (health, simulation, websocket, ecu)
│   │   ├── api/             # Dependency injection (singleton engine)
│   │   ├── websocket_manager.py
│   │   └── main.py
│   ├── dbc/
│   │   └── vael_can.dbc     # CAN database definition
│   └── tests/               # pytest test suite
├── frontend/
│   └── src/
│       ├── pages/           # 6 pages (Overview, Vehicle, ECU, CAN, Diagnostics, Tests)
│       ├── components/ui/   # MetricCard, Sidebar, TopBar
│       ├── hooks/           # useWebSocket
│       └── services/        # apiService, websocketService
├── scripts/                 # PowerShell startup scripts
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## 🧪 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/status` | Simulation status |
| GET | `/api/telemetry` | Current vehicle telemetry |
| GET | `/api/can/frames?limit=100` | Recent CAN frames |
| POST | `/api/simulation/start` | Start simulation |
| POST | `/api/simulation/stop` | Stop simulation |
| POST | `/api/simulation/pause` | Pause simulation |
| POST | `/api/simulation/resume` | Resume simulation |
| POST | `/api/simulation/reset` | Reset simulation |
| POST | `/api/simulation/config` | Update parameters |
| GET | `/api/ecus/status` | Per-ECU status |
| GET | `/api/ecus/can/messages` | DBC message definitions |
| WS | `/api/ws/live` | Real-time telemetry stream (2 Hz) |

---

## 🛠️ Tech Stack

**Backend:** Python 3.11 · FastAPI · Uvicorn · Pydantic v2 · cantools · threading  
**Frontend:** React 18 · TypeScript · Vite · Tailwind CSS · Recharts · Framer Motion · Axios  
**Testing:** pytest · pytest-asyncio · pytest-cov

---

## 📊 Simulation Scenarios

The engine simulates:
1. **Normal driving** — vehicle accelerates to target speed
2. **Obstacle approach** — obstacle at ~100m closing at -10 m/s
3. **FCW activation** — warning at ≤50m
4. **AEB activation** — emergency braking at ≤20m (ADAS → BRAKE_COMMAND → VCU)

---

## 📝 License

MIT — free to use, modify, and share.

---

*Built with ❤️ to showcase embedded systems simulation, automotive protocols, and full-stack development.*
