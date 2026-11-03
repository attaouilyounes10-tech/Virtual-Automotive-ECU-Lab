"""ADAS ECU Model - Phase 3 Implementation

Responsabilités :
- Traitement des données de détection d'obstacles (Obstacle_Distance_m, Relative_Speed_mps)
- Calcul du risque de collision (Collision_Risk_Level)
- Déclenchement FCW (Forward Collision Warning) et AEB (Autonomous Emergency Braking)
- Publication des trames CAN : ADAS_STATUS (0x100) et COLLISION_WARNING (0x101)
- Envoi de commandes de freinage d'urgence (BRAKE_COMMAND 0x201) via AEB

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


class ADAS_Ecu:
    """Advanced Driver Assistance Systems ECU implementation."""

    # Identifiants CAN (cohérence Phase 1 et Phase 2)
    CAN_ID_ADAS_STATUS = 0x100        # 256
    CAN_ID_COLLISION_WARNING = 0x101   # 257
    CAN_ID_BRAKE_COMMAND = 0x201       # 257 -> 0x201 pour AEB

    # Seuils de risque ADAS
    OBSTACLE_DISTANCE_WARNING_M = 50.0   # Distance seuil warning (m)
    OBSTACLE_DISTANCE_EMERGENCY_M = 20.0 # Distance seuil freinage d'urgence (m)
    RELATIVE_SPEED_CLOSING_THRESHOLD = -5.0  # Vitesse relative seuil (m/s)

    def __init__(self, ecus_id: str, can_bus: CANBus) -> None:
        """
        Initialise l'ECU ADAS.

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

        # État interne de l'ECU ADAS
        self.obstacle_detected = False
        self.obstacle_distance_m = 0.0
        self.relative_speed_mps = 0.0
        self.collision_risk_level = 0  # 0=None, 1=Low, 2=Medium, 3=High
        self.fcw_active = False
        self.aeb_active = False
        self.adas_mode = 1  # 1=Active, 0=Disabled

        # Enregistre cet ECU comme abonné au bus CAN
        self.subscriber = CANSubscriber(
            subscriber_id=f"ADAS_ECU_{ecus_id}",
            callback=self._handle_can_message,
        )
        self.can_bus.add_subscriber(self.subscriber)

    def _handle_can_message(self, frame: CANFrame) -> None:
        """
        Traite les messages CAN reçus sur le bus.
        L'ECU ADAS écoute principalement VEHICLE_STATUS (0x200).
        """
        self.message_history.append({
            "timestamp": datetime.now().timestamp(),
            "frame_id": frame.id,
            "data_hex": frame.data.hex(),
        })
        self.last_message_time = datetime.now().timestamp()

        try:
            decoded = self.dbc_loader.decode_can_frame(frame.id, frame.data)
            signals = decoded.get("signals", {})

            if frame.id == self.CAN_ID_ADAS_STATUS:
                # Réception de son propre statut (auto-monitoring)
                pass

            elif frame.id == 0x200:  # VEHICLE_STATUS
                vehicle_speed = signals.get("Vehicle_Speed_kmh", 0)
                brake_pressure = signals.get("Brake_Pressure_Bar", 0)
                operating_mode = signals.get("Operating_Mode", 0)
                # Mise à jour de l'état interne si nécessaire

        except Exception as e:
            print(f"[ADAS_ECU_{self.ecus_id}] Erreur décodage message 0x{frame.id:03X}: {e}")

    def update_obstacle_data(
        self,
        obstacle_detected: bool,
        obstacle_distance_m: float,
        relative_speed_mps: float,
    ) -> None:
        """
        Met à jour les données de détection d'obstacles et recalcule le risque.

        Args:
            obstacle_detected: Un obstacle est-il détecté ?
            obstacle_distance_m: Distance à l'obstacle en mètres
            relative_speed_mps: Vitesse relative en m/s (négatif = approche)
        """
        self.obstacle_detected = obstacle_detected
        self.obstacle_distance_m = obstacle_distance_m
        self.relative_speed_mps = relative_speed_mps

        # Recalcul du niveau de risque
        self._calculate_collision_risk()

        # Publication des trames CAN mises à jour
        self.publish_adas_status()
        self.publish_collision_warning()

        # Vérification AEB (freinage d'urgence autonome)
        self._check_aeb()

    def _calculate_collision_risk(self) -> None:
        """Calcule le niveau de risque de collision basé sur distance et vitesse relative."""
        if not self.obstacle_detected:
            self.collision_risk_level = 0
            self.fcw_active = False
            self.aeb_active = False
            return

        distance = self.obstacle_distance_m
        speed = self.relative_speed_mps

        # Logique de risque :
        # - Niveau 0 : Aucun risque
        # - Niveau 1 : Risque faible (distance > 50m)
        # - Niveau 2 : Risque moyen (20m < distance <= 50m)
        # - Niveau 3 : Risque élevé (distance <= 20m ou approche rapide)

        if distance <= self.OBSTACLE_DISTANCE_EMERGENCY_M:
            self.collision_risk_level = 3
        elif distance <= self.OBSTACLE_DISTANCE_WARNING_M:
            self.collision_risk_level = 2
        elif speed < self.RELATIVE_SPEED_CLOSING_THRESHOLD:
            self.collision_risk_level = 1
        else:
            self.collision_risk_level = 1 if self.obstacle_detected else 0

        # Activation FCW si niveau >= 2
        self.fcw_active = self.collision_risk_level >= 2

    def _check_aeb(self) -> None:
        """Vérifie si le freinage d'urgence autonome (AEB) doit être activé."""
        if self.collision_risk_level >= 3 and self.obstacle_detected:
            self.aeb_active = True
            # Envoi de commande de freinage d'urgence via BRAKE_COMMAND
            self._send_brake_command(emergency=True)
        else:
            self.aeb_active = False

    def _send_brake_command(self, emergency: bool = False) -> None:
        """
        Envoie une commande de freinage sur le bus CAN (trame BRAKE_COMMAND 0x201).

        Args:
            emergency: Si True, commande de freinage d'urgence
        """
        try:
            brake_force = 6000 if emergency else 2000  # Newton
            brake_duration = 250 if emergency else 200  # ms (max 255)

            signal_values = {
                "Brake_Request": 1,
                "Brake_Force_N": brake_force,
                "Brake_Duration_ms": brake_duration,
            }

            encoded = self.dbc_loader.encode_message(
                self.CAN_ID_BRAKE_COMMAND, signal_values
            )

            frame = CANFrame(
                id=self.CAN_ID_BRAKE_COMMAND,
                data=encoded,
                dlc=len(encoded),
                is_rtr=False,
            )
            self.can_bus.publish(frame)
            print(
                f"[ADAS_ECU_{self.ecus_id}] BRAKE_COMMAND envoyé: "
                f"force={brake_force}N, emergency={emergency}"
            )
        except Exception as e:
            print(f"[ADAS_ECU_{self.ecus_id}] Erreur envoi BRAKE_COMMAND: {e}")

    def publish_adas_status(self) -> None:
        """Publie la trame ADAS_STATUS (0x100) sur le bus CAN."""
        try:
            signal_values = {
                "ADAS_Active": 1 if self.is_active and self.adas_mode else 0,
                "ADAS_Mode": self.adas_mode,
                "Vehicle_Detected": 1 if self.obstacle_detected else 0,
                "Obstacle_Distance_m": min(655.35, max(0.0, round(self.obstacle_distance_m, 2))),
                "Relative_Speed_mps": max(-20.48, min(20.47, round(self.relative_speed_mps, 2))),
                "Collision_Risk_Level": self.collision_risk_level,
                "FCW_Active": 1 if self.fcw_active else 0,
                "AEB_Active": 1 if self.aeb_active else 0,
                "Reserved": 0,
            }

            encoded = self.dbc_loader.encode_message(
                self.CAN_ID_ADAS_STATUS, signal_values
            )

            frame = CANFrame(
                id=self.CAN_ID_ADAS_STATUS,
                data=encoded,
                dlc=len(encoded),
                is_rtr=False,
            )
            self.can_bus.publish(frame)

        except Exception as e:
            print(f"[ADAS_ECU_{self.ecus_id}] Erreur publication ADAS_STATUS: {e}")

    def publish_collision_warning(self) -> None:
        """Publie la trame COLLISION_WARNING (0x101) sur le bus CAN."""
        try:
            warning_level = min(self.collision_risk_level, 3)

            # Calcul TTC (Time To Collision) approximatif
            if self.relative_speed_mps < 0 and self.obstacle_distance_m > 0:
                ttc_s = self.obstacle_distance_m / abs(self.relative_speed_mps)
                ttc_s = min(ttc_s, 40.95)
            else:
                ttc_s = 0.0

            signal_values = {
                "Warning_Level": warning_level,
                "Time_To_Collision_s": round(ttc_s, 2),
                "Distance_At_Warning_m": min(655.35, max(0.0, round(self.obstacle_distance_m, 2))),
                "Closing_Speed_mps": max(-20.48, min(20.47, round(self.relative_speed_mps, 2))),
                "Warning_Type": 1 if self.fcw_active else 0,
                "Reserved": 0,
            }

            encoded = self.dbc_loader.encode_message(
                self.CAN_ID_COLLISION_WARNING, signal_values
            )

            frame = CANFrame(
                id=self.CAN_ID_COLLISION_WARNING,
                data=encoded,
                dlc=len(encoded),
                is_rtr=False,
            )
            self.can_bus.publish(frame)

        except Exception as e:
            print(f"[ADAS_ECU_{self.ecus_id}] Erreur publication COLLISION_WARNING: {e}")

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
        """Retourne le statut actuel de l'ECU ADAS."""
        return {
            "id": self.ecus_id,
            "type": "ADAS_ECU",
            "active": self.is_active,
            "connected": self.is_connected(),
            "last_message_time": self.last_message_time,
            "message_count": len(self.message_history),
            "obstacle_detected": self.obstacle_detected,
            "obstacle_distance_m": self.obstacle_distance_m,
            "relative_speed_mps": self.relative_speed_mps,
            "collision_risk_level": self.collision_risk_level,
            "fcw_active": self.fcw_active,
            "aeb_active": self.aeb_active,
            "adas_mode": self.adas_mode,
        }

    def enable(self) -> None:
        """Active l'ECU ADAS."""
        self.is_active = True
        self.adas_mode = 1

    def disable(self) -> None:
        """Désactive l'ECU ADAS."""
        self.is_active = False
        self.adas_mode = 0
        self.fcw_active = False
        self.aeb_active = False