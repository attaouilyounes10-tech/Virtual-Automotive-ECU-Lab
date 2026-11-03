"""Dashboard ECU Model - Phase 3 Implementation

Responsabilités :
- Réception et décodage des messages CAN provenant des autres ECUs
- Gestion des alertes et états du véhicule pour l'affichage tableau de bord
- Publication de la trame DASHBOARD_ALERT (0x300)
- Agrégation des informations ADAS et véhicule pour l'affichage

Interfaces :
- CAN Bus (Phase 1) pour la publication et la réception de trames
- DBC Loader (Phase 2) pour l'encodage/décodage des signaux selon vael_can.dbc
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..canbus.bus import CANBus
from ..canbus.frame import CANFrame
from ..canbus.subscriber import CANSubscriber
from ..canbus.dbc_loader import CANDbcLoader


class Dashboard_Ecu:
    """Dashboard ECU implementation."""

    # Identifiants CAN (cohérence Phase 1 et Phase 2)
    CAN_ID_DASHBOARD_ALERT = 0x300    # 768
    CAN_ID_ADAS_STATUS = 0x100        # 256
    CAN_ID_VEHICLE_STATUS = 0x200     # 512
    CAN_ID_COLLISION_WARNING = 0x101   # 257

    # Seuils d'alerte
    ALERT_SPEED_LIMIT_KMH = 130.0     # Limite de vitesse (km/h)
    ALERT_COLLISION_RISK_LEVEL = 2    # Niveau de risque d'alerte

    def __init__(self, ecus_id: str, can_bus: CANBus) -> None:
        """
        Initialise l'ECU Dashboard.

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

        # État d'affichage du tableau de bord
        self.current_speed_kmh = 0.0
        self.target_speed_kmh = 0.0
        self.brake_pressure_bar = 0.0
        self.collision_risk_level = 0
        self.fcw_active = False
        self.aeb_active = False
        self.obstacle_detected = False
        self.obstacle_distance_m = 0.0

        # Historique des alertes affichées
        self.alert_history: List[Dict[str, Any]] = []
        self.current_alert_type = 0
        self.current_alert_level = 0

        # Enregistre cet ECU comme abonné au bus CAN
        self.subscriber = CANSubscriber(
            subscriber_id=f"Dashboard_ECU_{ecus_id}",
            callback=self._handle_can_message,
        )
        self.can_bus.add_subscriber(self.subscriber)

    def _handle_can_message(self, frame: CANFrame) -> None:
        """
        Traite les messages CAN reçus sur le bus.
        Le Dashboard ECU écoute ADAS_STATUS (0x100), COLLISION_WARNING (0x101)
        et VEHICLE_STATUS (0x200).
        """
        self.message_history.append(frame)
        self.last_message_time = datetime.now().timestamp()

        try:
            decoded = self.dbc_loader.decode_can_frame(frame.id, frame.data)
            signals = decoded.get("signals", {})

            if frame.id == self.CAN_ID_ADAS_STATUS:
                self._process_adas_status(signals)

            elif frame.id == self.CAN_ID_COLLISION_WARNING:
                self._process_collision_warning(signals)

            elif frame.id == self.CAN_ID_VEHICLE_STATUS:
                self._process_vehicle_status(signals)

        except Exception as e:
            print(f"[Dashboard_ECU_{self.ecus_id}] Erreur décodage message 0x{frame.id:03X}: {e}")

    def _process_adas_status(self, signals: Dict[str, Any]) -> None:
        """Traite une trame ADAS_STATUS reçue."""
        self.obstacle_detected = bool(signals.get("Vehicle_Detected", 0))
        self.obstacle_distance_m = signals.get("Obstacle_Distance_m", 0.0)
        self.collision_risk_level = signals.get("Collision_Risk_Level", 0)
        self.fcw_active = bool(signals.get("FCW_Active", 0))
        self.aeb_active = bool(signals.get("AEB_Active", 0))

        # Génération d'alerte si risque de collision
        if self.collision_risk_level >= self.ALERT_COLLISION_RISK_LEVEL:
            self._raise_alert(
                alert_type=1,  # Alerte collision
                alert_level=self.collision_risk_level,
                message_id=100,
                alert_value=int(self.obstacle_distance_m * 100),  # cm
                active=True,
            )

    def _process_collision_warning(self, signals: Dict[str, Any]) -> None:
        """Traite une trame COLLISION_WARNING reçue."""
        warning_level = signals.get("Warning_Level", 0)
        ttc_s = signals.get("Time_To_Collision_s", 0.0)
        distance_m = signals.get("Distance_At_Warning_m", 0.0)

        if warning_level >= 2:
            self._raise_alert(
                alert_type=2,  # Alerte warning collision
                alert_level=warning_level,
                message_id=101,
                alert_value=int(distance_m * 100),
                active=True,
            )

    def _process_vehicle_status(self, signals: Dict[str, Any]) -> None:
        """Traite une trame VEHICLE_STATUS reçue."""
        self.current_speed_kmh = signals.get("Vehicle_Speed_kmh", 0.0)
        self.target_speed_kmh = signals.get("Target_Speed_kmh", 0.0)
        self.brake_pressure_bar = signals.get("Brake_Pressure_Bar", 0.0)

        # Alerte si vitesse excessive
        if self.current_speed_kmh > self.ALERT_SPEED_LIMIT_KMH:
            self._raise_alert(
                alert_type=3,  # Alerte vitesse excessive
                alert_level=2,
                message_id=102,
                alert_value=int(self.current_speed_kmh),
                active=True,
            )

    def _raise_alert(
        self,
        alert_type: int,
        alert_level: int,
        message_id: int,
        alert_value: int,
        active: bool = True,
    ) -> None:
        """
        Génère une alerte sur le tableau de bord et publie DASHBOARD_ALERT.

        Args:
            alert_type: Type d'alerte (1=collision, 2=warning, 3=vitesse, etc.)
            alert_level: Niveau de gravité (0-3)
            message_id: Identifiant du message d'alerte
            alert_value: Valeur associée à l'alerte
            active: Si l'alerte est active
        """
        alert = {
            "timestamp": datetime.now().timestamp(),
            "alert_type": alert_type,
            "alert_level": alert_level,
            "message_id": message_id,
            "alert_value": alert_value,
            "active": active,
        }
        self.alert_history.append(alert)
        self.current_alert_type = alert_type
        self.current_alert_level = alert_level

        # Publication de la trame DASHBOARD_ALERT (0x300)
        self.publish_dashboard_alert(
            alert_type=alert_type,
            alert_level=alert_level,
            message_id=message_id,
            alert_value=alert_value,
            active=active,
        )

    def publish_dashboard_alert(
        self,
        alert_type: int,
        alert_level: int,
        message_id: int,
        alert_value: int,
        active: bool,
    ) -> None:
        """Publie la trame DASHBOARD_ALERT (0x300) sur le bus CAN."""
        try:
            signal_values = {
                "Alert_Type": alert_type,
                "Alert_Level": alert_level,
                "Alert_Message_ID": message_id,
                "Alert_Value": alert_value,
                "Alert_Active": 1 if active else 0,
                "Alert_Count": len(self.alert_history),
                "Alert_Timestamp_s": int(datetime.now().timestamp()) % 8388607,
            }

            encoded = self.dbc_loader.encode_message(
                self.CAN_ID_DASHBOARD_ALERT, signal_values
            )

            frame = CANFrame(
                id=self.CAN_ID_DASHBOARD_ALERT,
                data=encoded,
                dlc=len(encoded),
                is_rtr=False,
            )
            self.can_bus.publish(frame)

        except Exception as e:
            print(f"[Dashboard_ECU_{self.ecus_id}] Erreur publication DASHBOARD_ALERT: {e}")

    def clear_alerts(self) -> None:
        """Efface toutes les alertes actives."""
        self.alert_history.clear()
        self.current_alert_type = 0
        self.current_alert_level = 0
        self.publish_dashboard_alert(
            alert_type=0,
            alert_level=0,
            message_id=0,
            alert_value=0,
            active=False,
        )

    def set_callback(self, callback_func) -> None:
        """Définit une fonction de rappel personnalisée pour la réception."""
        self.subscriber.set_callback(callback_func)

    def is_connected(self) -> bool:
        """Vérifie si l'ECU est connecté au bus CAN."""
        return self.is_active and self.can_bus is not None

    def get_message_history(self) -> list:
        """Retourne l'historique des messages reçus par cet ECU."""
        return self.message_history.copy()

    def get_alert_history(self) -> List[Dict[str, Any]]:
        """Retourne l'historique des alertes du tableau de bord."""
        return self.alert_history.copy()

    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut actuel de l'ECU Dashboard."""
        return {
            "id": self.ecus_id,
            "type": "Dashboard_ECU",
            "active": self.is_active,
            "connected": self.is_connected(),
            "last_message_time": self.last_message_time,
            "message_count": len(self.message_history),
            "current_speed_kmh": self.current_speed_kmh,
            "target_speed_kmh": self.target_speed_kmh,
            "brake_pressure_bar": self.brake_pressure_bar,
            "collision_risk_level": self.collision_risk_level,
            "fcw_active": self.fcw_active,
            "aeb_active": self.aeb_active,
            "obstacle_detected": self.obstacle_detected,
            "obstacle_distance_m": self.obstacle_distance_m,
            "current_alert_type": self.current_alert_type,
            "current_alert_level": self.current_alert_level,
            "alert_count": len(self.alert_history),
        }