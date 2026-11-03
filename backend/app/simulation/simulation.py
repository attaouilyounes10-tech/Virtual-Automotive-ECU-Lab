"""Simulation globale du véhicule - Phase 4

Ce module gère la simulation globale du véhicule, y compris :
- Cycle de vie (start, stop, pause, reset)
- Simulation des données du véhicule (vitesse, accélération, obstacles)
- Communication via le bus CAN et la DBC
- Intégration des trois ECU existantes (ADAS, VCU, Dashboard)
- Scénarios normaux et collisions
- Gestion du temps de simulation
"""

from __future__ import annotations
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import logging
from typing import Optional

from backend.app.canbus.bus import CANBus
from backend.app.canbus.frame import CANFrame
from backend.app.canbus.subscriber import CANSubscriber
from backend.app.canbus.dbc_loader import CANDbcLoader
from backend.app.canbus.errors import CANError
from backend.app.ecus.adas_ecu import ADAS_Ecu
from backend.app.ecus.vcu import VCU_Ecu
from backend.app.ecus.dashboard_ecu import Dashboard_Ecu

# Configuration de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simulation")

class SimulationEngine:
    """Moteur de simulation globale du véhicule."""

    def __init__(self,
                 bus_name: str = "simulation_bus",
                 adas_id: str = "adas_001",
                 vcu_id: str = "vcu_001",
                 dash_id: str = "dash_001"):
        """
        Initialise le moteur de simulation.

        Args:
            bus_name: Nom du bus CAN pour la simulation
            adas_id: Identifiant de l'ECU ADAS
            vcu_id: Identifiant de l'ECU VCU
            dash_id: Identifiant de l'ECU Dashboard
        """
        self.bus = CANBus(bus_name)
        self.adas = ADAS_Ecu(adas_id, self.bus)
        self.vcu = VCU_Ecu(vcu_id, self.bus)
        self.dash = Dashboard_Ecu(dash_id, self.bus)

        # Chargement de la base de données CAN
        self.dbc_loader = CANDbcLoader()
        self.dbc_loader.load()

        # État de la simulation
        self.is_running = False
        self.is_paused = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time = None
        self._elapsed_time = 0.0
        self._current_time = 0.0

        # Données de simulation
        self.vehicle_state = {
            'speed_kmh': 0.0,
            'target_speed_kmh': 0.0,
            'acceleration_mps2': 0.0,
            'throttle_position_pct': 0.0,
            'brake_pressure_bar': 0.0,
            'obstacle_detected': False,
            'obstacle_distance_m': 0.0,
            'relative_speed_mps': 0.0,
            'collision_risk_level': 0,
            'fcw_active': False,
            'aeb_active': False
        }

        # Scénario de conduite
        self.scenario = {
            'initial_speed': 0.0,
            'target_speed': 60.0,
            'acceleration_rate': 0.5,  # m/s^2
            'deceleration_rate': 2.0,  # m/s^2
            'obstacle_distance': 100.0,  # mètres
            'obstacle_speed': -10.0,   # m/s (approche)
            'collision_threshold': 20.0  # mètres
        }

        # Callback pour la simulation
        self.simulation_callback: Optional[Callable] = None

    def start(self) -> None:
        """Démarre la simulation."""
        if self.is_running:
            return

        self.is_running = True
        self.is_paused = False
        self._stop_event.clear()
        self._start_time = time.time()
        self._elapsed_time = 0.0
        self._current_time = 0.0

        # Reset vehicle state on fresh start
        self.vehicle_state = {
            'speed_kmh': 0.0,
            'target_speed_kmh': 0.0,
            'acceleration_mps2': 0.0,
            'throttle_position_pct': 0.0,
            'brake_pressure_bar': 0.0,
            'obstacle_detected': False,
            'obstacle_distance_m': 0.0,
            'relative_speed_mps': 0.0,
            'collision_risk_level': 0,
            'fcw_active': False,
            'aeb_active': False
        }

        logger.info("Simulation démarrée")

        # Connecter les ECU au bus
        self._connect_ecus()

        # Lancer le thread de simulation
        self._thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._thread.start()

        # Publier l'état initial (premier cycle)
        self._publish_initial_state()

    def stop(self) -> None:
        """Arrête la simulation."""
        if not self.is_running:
            return

        self.is_running = False
        self.is_paused = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        logger.info("Simulation arrêtée")

    def pause(self) -> None:
        """Met la simulation en pause."""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            logger.info("Simulation en pause")

    def resume(self) -> None:
        """Reprend la simulation après pause."""
        if self.is_running and self.is_paused:
            self.is_paused = False
            logger.info("Simulation reprise")

    def reset(self) -> None:
        """Réinitialise la simulation à son état initial."""
        self.stop()
        self.start()
        self.vehicle_state = {
            'speed_kmh': 0.0,
            'target_speed_kmh': 0.0,
            'acceleration_mps2': 0.0,
            'throttle_position_pct': 0.0,
            'brake_pressure_bar': 0.0,
            'obstacle_detected': False,
            'obstacle_distance_m': 0.0,
            'relative_speed_mps': 0.0,
            'collision_risk_level': 0,
            'fcw_active': False,
            'aeb_active': False
        }
        logger.info("Simulation réinitialisée")

    def set_simulation_callback(self, callback: Callable) -> None:
        """Définit une fonction de rappel appelée à chaque cycle de simulation."""
        self.simulation_callback = callback

    def _connect_ecus(self) -> None:
        """Connecte les ECU au bus CAN et configure leurs callbacks."""
        # ADAS ECU
        self.adas.subscriber.set_callback(self._adas_callback)

        # VCU ECU
        self.vcu.subscriber.set_callback(self._vcu_callback)

        # Dashboard ECU
        self.dash.subscriber.set_callback(self._dash_callback)

        logger.info("ECU connectées et callbacks configurés")

    def _publish_initial_state(self) -> None:
        """Publie l'état initial pour chaque ECU."""
        logger.info("Publication de l'état initial")

    def _adas_callback(self, frame: CANFrame) -> None:
        """Callback for the ADAS subscriber.
        No-op: vehicle_state is synced directly from self.adas.* in the simulation loop,
        so we don't read back from the CAN frame to avoid stale-value feedback loops.
        """
        pass

    def _vcu_callback(self, frame: CANFrame) -> None:
        """Callback pour l'ECU VCU."""
        try:
            decoded = self.dbc_loader.decode_can_frame(frame.id, frame.data)
            signals = decoded.get("signals", {})

            # Traitement des commandes de freinage
            if frame.id == 0x201:  # BRAKE_COMMAND
                self._process_brake_command(signals)

        except Exception as e:
            logger.error(f"Erreur dans _vcu_callback: {e}")

    def _dash_callback(self, frame: CANFrame) -> None:
        """Callback pour l'ECU Dashboard."""
        try:
            decoded = self.dbc_loader.decode_can_frame(frame.id, frame.data)
            signals = decoded.get("signals", {})

            # Traitement des alertes
            if frame.id == 0x300:  # DASHBOARD_ALERT
                self._process_dashboard_alert(signals)

        except Exception as e:
            logger.error(f"Erreur dans _dash_callback: {e}")

    def _process_brake_command(self, signals: Dict[str, Any]) -> None:
        """Traite une commande de freinage reçue."""
        brake_request = signals.get("Brake_Request", 0)
        brake_force_n = signals.get("Brake_Force_N", 0)
        brake_duration_ms = signals.get("Brake_Duration_ms", 0)
        emergency_brake = signals.get("Emergency_Brake", 0)

        if brake_request == 1:
            # Application du freinage
            deceleration = min(brake_force_n / 1000.0 * 0.01, self.scenario['deceleration_rate'])
            self.vehicle_state['acceleration_mps2'] = -deceleration
            self.vehicle_state['brake_pressure_bar'] = min(self.vehicle_state['brake_pressure_bar'] + 5.0, 40.95)

            # Réduction de la vitesse
            decel_kmh = deceleration * 3.6
            self.vehicle_state['speed_kmh'] = max(0.0, self.vehicle_state['speed_kmh'] - decel_kmh)

            logger.info(f"[VCU] Freinage appliqué: {brake_force_n}N, {brake_duration_ms}ms")

    def _process_dashboard_alert(self, signals: Dict[str, Any]) -> None:
        """Traite une alerte du Dashboard ECU — lecture seule, pas de surcharge de l'état ADAS."""
        alert_type = signals.get("Alert_Type", 0)
        alert_level = signals.get("Alert_Level", 0)
        # Dashboard alerts are informational; vehicle_state collision risk is
        # authoritative from ADAS ECU (synced in _update_obstacle_scenario).
        logger.debug(f"Dashboard alert type={alert_type} level={alert_level}")

    def _publish_adas_status(self) -> None:
        """Publie la trame ADAS_STATUS sur le bus CAN depuis l'état de l'ECU ADAS."""
        try:
            # Read authoritative values from the ADAS ECU, not vehicle_state
            rel_speed = max(-20.48, min(20.47, self.adas.relative_speed_mps))
            signal_values = {
                "ADAS_Active": 1 if self.adas.is_active and self.adas.adas_mode else 0,
                "ADAS_Mode": self.adas.adas_mode,
                "Vehicle_Detected": 1 if self.adas.obstacle_detected else 0,
                "Obstacle_Distance_m": min(655.35, max(0.0, self.adas.obstacle_distance_m)),
                "Relative_Speed_mps": rel_speed,
                "Collision_Risk_Level": int(self.adas.collision_risk_level),
                "FCW_Active": 1 if self.adas.fcw_active else 0,
                "AEB_Active": 1 if self.adas.aeb_active else 0,
                "Reserved": 0,
            }

            encoded = self.dbc_loader.encode_message(0x100, signal_values)
            frame = CANFrame(
                id=0x100,
                data=encoded,
                dlc=len(encoded),
                is_rtr=False,
            )
            self.bus.publish(frame)

        except Exception as e:
            logger.error(f"Erreur publication ADAS_STATUS: {e}")

    def _update_simulation_state(self, delta_time: float) -> None:
        """Met à jour l'état de simulation."""
        # Gestion du freinage naturel
        if self.vehicle_state['throttle_position_pct'] == 0:
            self.vehicle_state['acceleration_mps2'] = -0.5  # Freinage naturel
        else:
            self.vehicle_state['acceleration_mps2'] = self.vehicle_state['throttle_position_pct'] * 0.05

        # Mise à jour de la vitesse
        self.vehicle_state['speed_kmh'] += self.vehicle_state['acceleration_mps2'] * 3.6 * delta_time
        self.vehicle_state['speed_kmh'] = max(0.0, self.vehicle_state['speed_kmh'])

        # Mise à jour de la vitesse cible
        if self.vehicle_state['speed_kmh'] < self.vehicle_state['target_speed_kmh']:
            self.vehicle_state['speed_kmh'] += 0.5  # Accélération progressive
        elif self.vehicle_state['speed_kmh'] > self.vehicle_state['target_speed_kmh']:
            self.vehicle_state['speed_kmh'] = max(0.0, self.vehicle_state['speed_kmh'] - 0.5)

    def _update_obstacle_scenario(self, delta_time: float) -> None:
        """Met à jour le scénario d'obstacle en synchronisant depuis l'ADAS ECU."""
        # Primary source of truth for ADAS-computed values is the ADAS ECU itself
        self.vehicle_state['obstacle_detected'] = self.adas.obstacle_detected
        self.vehicle_state['obstacle_distance_m'] = self.adas.obstacle_distance_m
        self.vehicle_state['relative_speed_mps'] = self.adas.relative_speed_mps
        self.vehicle_state['collision_risk_level'] = self.adas.collision_risk_level
        self.vehicle_state['fcw_active'] = self.adas.fcw_active
        self.vehicle_state['aeb_active'] = self.adas.aeb_active

        if not self.vehicle_state['obstacle_detected']:
            return

        # Advance obstacle distance based on relative speed
        self.vehicle_state['obstacle_distance_m'] -= self.vehicle_state['relative_speed_mps'] * delta_time
        self.vehicle_state['obstacle_distance_m'] = max(0.0, self.vehicle_state['obstacle_distance_m'])

        # Keep ADAS ECU in sync with updated distance
        self.adas.obstacle_distance_m = self.vehicle_state['obstacle_distance_m']

    def _simulation_loop(self) -> None:
        """Boucle principale de simulation."""
        while not self._stop_event.is_set():
            if self.is_paused:
                time.sleep(0.1)
                continue

            # Calcul du temps écoulé
            current_time = time.time()
            if self._start_time is None:
                self._start_time = current_time
                self._current_time = 0.0
            else:
                self._current_time = current_time - self._start_time
                self._elapsed_time = self._current_time

            # Mise à jour de la simulation
            delta_time = 0.1  # 100ms de pas de temps
            self._update_simulation_state(delta_time)
            self._update_obstacle_scenario(delta_time)

            # Publication des messages CAN par les ECU
            self._publish_ecu_messages()

            # Publication des données (optionnel)
            if self.simulation_callback:
                self.simulation_callback()

            time.sleep(0.02)  # 20ms pour éviter surcharge CPU

    def _publish_ecu_messages(self) -> None:
        """Publie les messages CAN par les ECU."""
        try:
            # ADAS publie ADAS_STATUS
            self._publish_adas_status()

            # VCU publie VEHICLE_STATUS
            self._publish_vehicle_status()

            # Dashboard publie DASHBOARD_ALERT si nécessaire
            if self.vehicle_state['collision_risk_level'] > 0:
                self._publish_dashboard_alert()

        except Exception as e:
            logger.error(f"Erreur publication messages ECU: {e}")

    def _publish_vehicle_status(self) -> None:
        """Publie la trame VEHICLE_STATUS (0x200) sur le bus CAN."""
        try:
            signal_values = {
                "Vehicle_Speed_kmh": round(self.vehicle_state['speed_kmh'], 2),
                "Target_Speed_kmh": round(self.vehicle_state['target_speed_kmh'], 2),
                "Acceleration_mps2": round(self.vehicle_state['acceleration_mps2'], 2),
                "Throttle_Position_Pct": round(self.vehicle_state['throttle_position_pct'], 1),
                "Brake_Pressure_Bar": round(self.vehicle_state['brake_pressure_bar'], 2),
            }

            encoded = self.dbc_loader.encode_message(0x200, signal_values)
            frame = CANFrame(
                id=0x200,
                data=encoded,
                dlc=len(encoded),
                is_rtr=False,
            )
            self.bus.publish(frame)

        except Exception as e:
            logger.error(f"Publication VEHICLE_STATUS: {e}")

    def _publish_dashboard_alert(self) -> None:
        """Publie une trame DASHBOARD_ALERT (0x300)."""
        try:
            signal_values = {
                "Alert_Type": 1 if self.vehicle_state['collision_risk_level'] > 0 else 0,
                "Alert_Level": self.vehicle_state['collision_risk_level'],
                "Alert_Message_ID": 100,
                "Alert_Value": int(self.vehicle_state['obstacle_distance_m'] * 100),
                "Alert_Active": 1,
                "Alert_Count": 1,
                "Alert_Timestamp_s": int(time.time()) % 8388607,
            }

            encoded = self.dbc_loader.encode_message(0x300, signal_values)
            frame = CANFrame(
                id=0x300,
                data=encoded,
                dlc=len(encoded),
                is_rtr=False,
            )
            self.bus.publish(frame)

        except Exception as e:
            logger.error(f"Publication DASHBOARD_ALERT: {e}")

    def get_simulation_state(self) -> Dict[str, Any]:
        """Retourne l'état actuel de la simulation."""
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'current_time': self._current_time,
            'elapsed_time': self._elapsed_time,
            'vehicle_state': self.vehicle_state.copy()
        }

# Exemple d'utilisation
if __name__ == "__main__":
    def callback():
        state = SimulationEngine().get_simulation_state()
        print(f"Temps: {state['current_time']:.1f}s | Vitesse: {state['vehicle_state']['speed_kmh']:.1f} km/h")

# simulation = SimulationEngine()
# simulation.start()
# time.sleep(5)
# simulation.stop()