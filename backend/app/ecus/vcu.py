"""Vehicle Control ECU (VCU) Model - Phase 3 Implementation

Responsabilités :
- Gestion de la vitesse, de l'accélération et du freinage du véhicule
- Traitement des commandes de freinage (BRAKE_COMMAND 0x201) provenant de l'ADAS ECU
- Publication de la trame VEHICLE_STATUS (0x200)
- Maintien de l'état dynamique du véhicule (vitesse cible, accélération, pression de freinage)

Interfaces :
- CAN Bus (Phase 1) pour la publication et la réception de trames
- DBC Loader (Phase 2) pour l'encodage/décodage des signaux selon vael_can.dbc
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime
from ..canbus.bus import CANBus
from ..canbus.frame import CANFrame
from ..canbus.subscriber import CANSubscriber
from ..canbus.dbc_loader import CANDbcLoader


class VCU_Ecu:
    """Vehicle Control ECU implementation."""

    # Identifiants CAN (cohérence Phase 1 et Phase 2)
    CAN_ID_VEHICLE_STATUS = 0x200   # 512
    CAN_ID_BRAKE_COMMAND = 0x201    # 513

    def __init__(self, ecus_id: str, can_bus: CANBus) -> None:
        """
        Initialise l'ECU VCU.

        Args:
            ecus_id: Identifiant unique de cet ECU
            can_bus: Instance du bus CAN pour communiquer avec les autres ECUs
        """
        self.ecus_id = ecus_id
        self.can_bus = can_bus
        self.dbc_loader = CANDbcLoader()
        self.dbc_loader.load()

        self.is_active = True
        self.last_message_time = datetime.now().timestamp()
        self.message_history = []  # Historique des messages reçus

        # État interne du véhicule (simulé)
        self.vehicle_speed_kmh = 0.0
        self.target_speed_kmh = 0.0
        self.acceleration_mps2 = 0.0
        self.throttle_position_pct = 0.0
        self.brake_pressure_bar = 0.0

        # Enregistre cet ECU comme abonné au bus CAN
        self.subscriber = CANSubscriber(
            subscriber_id=f"VCU_{ecus_id}",
            callback=self._handle_can_message,
        )
        self.can_bus.add_subscriber(self.subscriber)

    def _handle_can_message(self, frame: CANFrame) -> None:
        """
        Traite les messages CAN reçus sur le bus.
        L'ECU VCU écoute principalement BRAKE_COMMAND (0x201).
        """
        self.message_history.append(frame)
        self.last_message_time = datetime.now().timestamp()

        try:
            decoded = self.dbc_loader.decode_can_frame(frame.id, frame.data)
            signals = decoded.get("signals", {})

            if frame.id == self.CAN_ID_BRAKE_COMMAND:
                self._process_brake_command(signals)

        except Exception as e:
            print(f"[VCU_{self.ecus_id}] Erreur décodage message 0x{frame.id:03X}: {e}")

    def _process_brake_command(self, signals: Dict[str, Any]) -> None:
        """
        Traite une commande de freinage reçue (BRAKE_COMMAND 0x201).

        Args:
            signals: Signaux décodés de la trame BRAKE_COMMAND
        """
        brake_request = signals.get("Brake_Request", 0)
        brake_force_n = signals.get("Brake_Force_N", 0)
        brake_duration_ms = signals.get("Brake_Duration_ms", 0)

        if brake_request == 1:
            # Application du freinage
            if brake_force_n >= 5000:  # Freinage d'urgence
                self.brake_pressure_bar = min(self.brake_pressure_bar + 10.0, 40.95)
                self.acceleration_mps2 = -5.0  # Décélération forte
            else:
                self.brake_pressure_bar = min(self.brake_pressure_bar + 5.0, 40.95)
                self.acceleration_mps2 = -2.0  # Décélération modérée

            # Réduction de la vitesse proportionnelle à la force de freinage
            decel = (brake_force_n / 1000.0) * 0.01
            self.vehicle_speed_kmh = max(0.0, self.vehicle_speed_kmh - decel)

            print(
                f"[VCU_{self.ecus_id}] BRAKE_COMMAND reçu: "
                f"force={brake_force_n}N, durée={brake_duration_ms}ms"
            )
        else:
            # Relâchement du frein
            self.brake_pressure_bar = max(0.0, self.brake_pressure_bar - 2.0)
            self.acceleration_mps2 = 0.0

    def update_vehicle_state(
        self,
        target_speed_kmh: float,
        throttle_position_pct: float,
    ) -> None:
        """
        Met à jour l'état du véhicule (appelé par la simulation ou l'utilisateur).

        Args:
            target_speed_kmh: Vitesse cible en km/h
            throttle_position_pct: Position de l'accélérateur en pourcentage
        """
        self.target_speed_kmh = target_speed_kmh
        self.throttle_position_pct = throttle_position_pct

        # Simulation simple de l'accélération basée sur l'accélérateur
        if throttle_position_pct > 0:
            self.acceleration_mps2 = throttle_position_pct * 0.05  # m/s^2
            # Augmentation de la vitesse
            self.vehicle_speed_kmh = min(
                self.vehicle_speed_kmh + self.acceleration_mps2 * 3.6,
                self.target_speed_kmh,
            )
        else:
            self.acceleration_mps2 = 0.0
            # Ralenti naturel (frottements)
            self.vehicle_speed_kmh = max(0.0, self.vehicle_speed_kmh - 0.5)

        # Publication de la trame VEHICLE_STATUS
        self.publish_vehicle_status()

    def publish_vehicle_status(self) -> None:
        """Publie la trame VEHICLE_STATUS (0x200) sur le bus CAN."""
        try:
            signal_values = {
                "Vehicle_Speed_kmh": round(self.vehicle_speed_kmh, 2),
                "Target_Speed_kmh": round(self.target_speed_kmh, 2),
                "Acceleration_mps2": round(self.acceleration_mps2, 2),
                "Throttle_Position_Pct": round(self.throttle_position_pct, 1),
                "Brake_Pressure_Bar": round(self.brake_pressure_bar, 2),
            }

            encoded = self.dbc_loader.encode_message(
                self.CAN_ID_VEHICLE_STATUS, signal_values
            )

            frame = CANFrame(
                id=self.CAN_ID_VEHICLE_STATUS,
                data=encoded,
                dlc=len(encoded),
                is_rtr=False,
            )
            self.can_bus.publish(frame)

        except Exception as e:
            print(f"[VCU_{self.ecus_id}] Erreur publication VEHICLE_STATUS: {e}")

    def set_callback(self, callback_func) -> None:
        """Définit une fonction de rappel personnalisée pour la réception."""
        self.subscriber.set_callback(callback_func)

    def is_connected(self) -> bool:
        """Vérifie si l'ECU est connecté au bus CAN."""
        return self.is_active and self.can_bus is not None

    def get_message_history(self) -> list:
        """Retourne l'historique des messages reçus par cet ECU."""
        return self.message_history.copy()

    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut actuel de l'ECU VCU."""
        return {
            "id": self.ecus_id,
            "type": "VCU",
            "active": self.is_active,
            "connected": self.is_connected(),
            "last_message_time": self.last_message_time,
            "message_count": len(self.message_history),
            "vehicle_speed_kmh": self.vehicle_speed_kmh,
            "target_speed_kmh": self.target_speed_kmh,
            "acceleration_mps2": self.acceleration_mps2,
            "throttle_position_pct": self.throttle_position_pct,
            "brake_pressure_bar": self.brake_pressure_bar,
        }

    def emergency_stop(self) -> None:
        """Arrêt d'urgence du véhicule (simulation uniquement)."""
        self.target_speed_kmh = 0.0
        self.throttle_position_pct = 0.0
        self.brake_pressure_bar = 40.95
        self.acceleration_mps2 = -8.0
        self.vehicle_speed_kmh = max(0.0, self.vehicle_speed_kmh - 10.0)
        self.publish_vehicle_status()