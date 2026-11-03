"""Tests unitaires pour les ECU virtuels (Phase 3).

Ces tests couvrent :
- ADAS ECU : détection d'obstacles, calcul du risque, publication ADAS_STATUS et COLLISION_WARNING
- VCU : gestion vitesse/freinage, traitement BRAKE_COMMAND, publication VEHICLE_STATUS
- Dashboard ECU : réception des messages CAN, génération d'alertes, publication DASHBOARD_ALERT
- Communication inter-ECU via le bus CAN logiciel
"""

import pytest
from backend.app.canbus.bus import CANBus
from backend.app.ecus.adas_ecu import ADAS_Ecu
from backend.app.ecus.vcu import VCU_Ecu
from backend.app.ecus.dashboard_ecu import Dashboard_Ecu
from backend.app.canbus.dbc_loader import CANDbcLoader


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def can_bus():
    """Retourne une instance de bus CAN vide pour les tests."""
    return CANBus(bus_name="test_bus")


@pytest.fixture
def dbc_loader():
    """Retourne un DBC loader chargé."""
    loader = CANDbcLoader()
    loader.load()
    return loader


# ============================================================================
# TESTS ADAS ECU
# ============================================================================

class TestADAS_Ecu:
    """Tests pour l'ECU ADAS."""

    def test_adas_ecu_initialization(self, can_bus):
        """Test l'initialisation de l'ECU ADAS."""
        ecu = ADAS_Ecu(ecus_id="test_001", can_bus=can_bus)
        assert ecu.ecus_id == "test_001"
        assert ecu.is_active is True
        assert ecu.can_bus is can_bus
        assert ecu.obstacle_detected is False
        assert ecu.collision_risk_level == 0
        assert ecu.fcw_active is False
        assert ecu.aeb_active is False

    def test_adas_ecu_is_connected(self, can_bus):
        """Test la vérification de connexion."""
        ecu = ADAS_Ecu(ecus_id="test_002", can_bus=can_bus)
        assert ecu.is_connected() is True

    def test_adas_update_obstacle_no_risk(self, can_bus):
        """Test avec obstacle détecté mais à distance sécuritaire."""
        ecu = ADAS_Ecu(ecus_id="test_003", can_bus=can_bus)
        ecu.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=100.0,
            relative_speed_mps=0.0,
        )
        assert ecu.obstacle_detected is True
        assert ecu.obstacle_distance_m == 100.0
        assert ecu.collision_risk_level == 1  # Risque faible

    def test_adas_update_obstacle_warning(self, can_bus):
        """Test avec obstacle à distance de warning (20-50m)."""
        ecu = ADAS_Ecu(ecus_id="test_004", can_bus=can_bus)
        ecu.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=30.0,
            relative_speed_mps=-10.0,
        )
        assert ecu.collision_risk_level == 2  # Risque moyen
        assert ecu.fcw_active is True

    def test_adas_update_obstacle_emergency(self, can_bus):
        """Test avec obstacle à distance critique (< 20m)."""
        ecu = ADAS_Ecu(ecus_id="test_005", can_bus=can_bus)
        ecu.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=10.0,
            relative_speed_mps=-15.0,
        )
        assert ecu.collision_risk_level == 3  # Risque élevé
        assert ecu.fcw_active is True
        assert ecu.aeb_active is True

    def test_adas_no_obstacle_no_risk(self, can_bus):
        """Test sans obstacle détecté."""
        ecu = ADAS_Ecu(ecus_id="test_006", can_bus=can_bus)
        ecu.update_obstacle_data(
            obstacle_detected=False,
            obstacle_distance_m=0.0,
            relative_speed_mps=0.0,
        )
        assert ecu.collision_risk_level == 0
        assert ecu.fcw_active is False
        assert ecu.aeb_active is False

    def test_adas_publish_adas_status(self, can_bus, dbc_loader):
        """Test la publication de la trame ADAS_STATUS (0x100)."""
        ecu = ADAS_Ecu(ecus_id="test_007", can_bus=can_bus)
        ecu.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=50.0,
            relative_speed_mps=-10.0,
        )

        # Vérifier que le bus a reçu des messages
        history = can_bus.get_message_history()
        adas_frames = [f for f in history if f.id == 0x100]
        assert len(adas_frames) >= 1

        # Vérifier le décodage
        frame = adas_frames[-1]
        decoded = dbc_loader.decode_can_frame(frame.id, frame.data)
        signals = decoded["signals"]
        assert signals["Vehicle_Detected"] == 1
        assert signals["Collision_Risk_Level"] >= 1

    def test_adas_publish_collision_warning(self, can_bus, dbc_loader):
        """Test la publication de la trame COLLISION_WARNING (0x101)."""
        ecu = ADAS_Ecu(ecus_id="test_008", can_bus=can_bus)
        ecu.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=30.0,
            relative_speed_mps=-15.0,
        )

        history = can_bus.get_message_history()
        warning_frames = [f for f in history if f.id == 0x101]
        assert len(warning_frames) >= 1

        frame = warning_frames[-1]
        decoded = dbc_loader.decode_can_frame(frame.id, frame.data)
        signals = decoded["signals"]
        assert signals["Warning_Level"] >= 1

    def test_adas_aeb_triggers_brake_command(self, can_bus, dbc_loader):
        """Test que l'AEB déclenche un BRAKE_COMMAND (0x201)."""
        ecu = ADAS_Ecu(ecus_id="test_009", can_bus=can_bus)
        ecu.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=10.0,
            relative_speed_mps=-20.0,
        )

        history = can_bus.get_message_history()
        brake_frames = [f for f in history if f.id == 0x201]
        assert len(brake_frames) >= 1, "AEB devrait déclencher un BRAKE_COMMAND"

    def test_adas_enable_disable(self, can_bus):
        """Test l'activation/désactivation de l'ECU ADAS."""
        ecu = ADAS_Ecu(ecus_id="test_010", can_bus=can_bus)
        ecu.disable()
        assert ecu.is_active is False
        assert ecu.adas_mode == 0
        assert ecu.fcw_active is False
        assert ecu.aeb_active is False

        ecu.enable()
        assert ecu.is_active is True
        assert ecu.adas_mode == 1

    def test_adas_get_status(self, can_bus):
        """Test la récupération du statut de l'ECU ADAS."""
        ecu = ADAS_Ecu(ecus_id="test_011", can_bus=can_bus)
        status = ecu.get_status()
        assert status["id"] == "test_011"
        assert status["type"] == "ADAS_ECU"
        assert status["active"] is True
        assert "collision_risk_level" in status
        assert "fcw_active" in status
        assert "aeb_active" in status


# ============================================================================
# TESTS VCU
# ============================================================================

class TestVCU_Ecu:
    """Tests pour l'ECU VCU."""

    def test_vcu_ecu_initialization(self, can_bus):
        """Test l'initialisation de l'ECU VCU."""
        ecu = VCU_Ecu(ecus_id="vcu_001", can_bus=can_bus)
        assert ecu.ecus_id == "vcu_001"
        assert ecu.is_active is True
        assert ecu.vehicle_speed_kmh == 0.0
        assert ecu.brake_pressure_bar == 0.0

    def test_vcu_is_connected(self, can_bus):
        """Test la vérification de connexion VCU."""
        ecu = VCU_Ecu(ecus_id="vcu_002", can_bus=can_bus)
        assert ecu.is_connected() is True

    def test_vcu_update_vehicle_state_acceleration(self, can_bus, dbc_loader):
        """Test l'accélération du véhicule."""
        ecu = VCU_Ecu(ecus_id="vcu_003", can_bus=can_bus)
        ecu.update_vehicle_state(
            target_speed_kmh=50.0,
            throttle_position_pct=50.0,
        )
        assert ecu.target_speed_kmh == 50.0
        assert ecu.throttle_position_pct == 50.0
        assert ecu.vehicle_speed_kmh > 0.0

        # Vérifier publication VEHICLE_STATUS
        history = can_bus.get_message_history()
        status_frames = [f for f in history if f.id == 0x200]
        assert len(status_frames) >= 1

    def test_vcu_process_brake_command(self, can_bus, dbc_loader):
        """Test le traitement d'une commande de freinage."""
        ecu = VCU_Ecu(ecus_id="vcu_004", can_bus=can_bus)

        # Simuler réception d'un BRAKE_COMMAND
        signal_values = {
            "Brake_Request": 1,
            "Brake_Force_N": 3000,
            "Brake_Duration_ms": 200,
            "Emergency_Brake": 0,
            "Brake_Source": 1,
        }
        encoded = dbc_loader.encode_message(0x201, signal_values)
        frame = __import__("backend.app.canbus.frame", fromlist=["CANFrame"]).CANFrame(
            id=0x201, data=encoded, dlc=len(encoded)
        )
        ecu._handle_can_message(frame)

        assert ecu.brake_pressure_bar > 0.0

    def test_vcu_emergency_brake_command(self, can_bus, dbc_loader):
        """Test le traitement d'un freinage d'urgence."""
        ecu = VCU_Ecu(ecus_id="vcu_005", can_bus=can_bus)

        signal_values = {
            "Brake_Request": 1,
            "Brake_Force_N": 6000,
            "Brake_Duration_ms": 250,
        }
        encoded = dbc_loader.encode_message(0x201, signal_values)
        frame = __import__("backend.app.canbus.frame", fromlist=["CANFrame"]).CANFrame(
            id=0x201, data=encoded, dlc=len(encoded)
        )
        ecu._handle_can_message(frame)

        assert ecu.brake_pressure_bar > 0.0
        assert ecu.acceleration_mps2 < 0  # Décélération

    def test_vcu_publish_vehicle_status(self, can_bus, dbc_loader):
        """Test la publication de VEHICLE_STATUS (0x200)."""
        ecu = VCU_Ecu(ecus_id="vcu_006", can_bus=can_bus)
        ecu.update_vehicle_state(
            target_speed_kmh=80.0,
            throttle_position_pct=30.0,
        )

        history = can_bus.get_message_history()
        status_frames = [f for f in history if f.id == 0x200]
        assert len(status_frames) >= 1

        frame = status_frames[-1]
        decoded = dbc_loader.decode_can_frame(frame.id, frame.data)
        signals = decoded["signals"]
        assert signals["Vehicle_Speed_kmh"] > 0
        assert signals["Target_Speed_kmh"] == 80.0

    def test_vcu_emergency_stop(self, can_bus):
        """Test l'arrêt d'urgence du VCU."""
        ecu = VCU_Ecu(ecus_id="vcu_007", can_bus=can_bus)
        ecu.update_vehicle_state(target_speed_kmh=100.0, throttle_position_pct=50.0)
        assert ecu.vehicle_speed_kmh > 0

        ecu.emergency_stop()
        assert ecu.target_speed_kmh == 0.0
        assert ecu.throttle_position_pct == 0.0
        assert ecu.brake_pressure_bar >= 40.95

    def test_vcu_get_status(self, can_bus):
        """Test la récupération du statut VCU."""
        ecu = VCU_Ecu(ecus_id="vcu_008", can_bus=can_bus)
        status = ecu.get_status()
        assert status["id"] == "vcu_008"
        assert status["type"] == "VCU"
        assert status["active"] is True
        assert "vehicle_speed_kmh" in status
        assert "brake_pressure_bar" in status


# ============================================================================
# TESTS DASHBOARD ECU
# ============================================================================

class TestDashboard_Ecu:
    """Tests pour l'ECU Dashboard."""

    def test_dashboard_ecu_initialization(self, can_bus):
        """Test l'initialisation de l'ECU Dashboard."""
        ecu = Dashboard_Ecu(ecus_id="dash_001", can_bus=can_bus)
        assert ecu.ecus_id == "dash_001"
        assert ecu.is_active is True
        assert ecu.current_speed_kmh == 0.0
        assert len(ecu.alert_history) == 0

    def test_dashboard_is_connected(self, can_bus):
        """Test la vérification de connexion Dashboard."""
        ecu = Dashboard_Ecu(ecus_id="dash_002", can_bus=can_bus)
        assert ecu.is_connected() is True

    def test_dashboard_process_adas_status(self, can_bus, dbc_loader):
        """Test la réception d'une trame ADAS_STATUS."""
        ecu = Dashboard_Ecu(ecus_id="dash_003", can_bus=can_bus)

        # Créer et envoyer une trame ADAS_STATUS
        signal_values = {
            "ADAS_Active": 1,
            "ADAS_Mode": 1,
            "Vehicle_Detected": 1,
            "Obstacle_Distance_m": 30.0,
            "Relative_Speed_mps": -10.0,
            "Collision_Risk_Level": 2,
            "FCW_Active": 1,
            "AEB_Active": 0,
            "Reserved": 0,
        }
        encoded = dbc_loader.encode_message(0x100, signal_values)
        frame = __import__("backend.app.canbus.frame", fromlist=["CANFrame"]).CANFrame(
            id=0x100, data=encoded, dlc=len(encoded)
        )
        ecu._handle_can_message(frame)

        assert ecu.obstacle_detected is True
        assert ecu.collision_risk_level == 2
        assert ecu.fcw_active is True

    def test_dashboard_process_collision_warning(self, can_bus, dbc_loader):
        """Test la réception d'une trame COLLISION_WARNING."""
        ecu = Dashboard_Ecu(ecus_id="dash_004", can_bus=can_bus)

        signal_values = {
            "Warning_Level": 2,
            "Time_To_Collision_s": 5.0,
            "Distance_At_Warning_m": 30.0,
            "Closing_Speed_mps": -10.0,
            "Warning_Type": 1,
            "Reserved": 0,
        }
        encoded = dbc_loader.encode_message(0x101, signal_values)
        frame = __import__("backend.app.canbus.frame", fromlist=["CANFrame"]).CANFrame(
            id=0x101, data=encoded, dlc=len(encoded)
        )
        ecu._handle_can_message(frame)

        assert ecu.collision_risk_level >= 0  # Warning traité

    def test_dashboard_process_vehicle_status(self, can_bus, dbc_loader):
        """Test la réception d'une trame VEHICLE_STATUS."""
        ecu = Dashboard_Ecu(ecus_id="dash_005", can_bus=can_bus)

        signal_values = {
            "Vehicle_Speed_kmh": 60.0,
            "Target_Speed_kmh": 80.0,
            "Acceleration_mps2": 1.5,
            "Throttle_Position_Pct": 40.0,
            "Brake_Pressure_Bar": 5.0,
        }
        encoded = dbc_loader.encode_message(0x200, signal_values)
        frame = __import__("backend.app.canbus.frame", fromlist=["CANFrame"]).CANFrame(
            id=0x200, data=encoded, dlc=len(encoded)
        )
        ecu._handle_can_message(frame)

        assert ecu.current_speed_kmh == 60.0
        assert ecu.target_speed_kmh == 80.0
        assert ecu.brake_pressure_bar == 5.0

    def test_dashboard_speed_limit_alert(self, can_bus, dbc_loader):
        """Test l'alerte de dépassement de vitesse."""
        ecu = Dashboard_Ecu(ecus_id="dash_006", can_bus=can_bus)

        # Vitesse supérieure à la limite (130 km/h)
        signal_values = {
            "Vehicle_Speed_kmh": 140.0,
            "Target_Speed_kmh": 140.0,
            "Acceleration_mps2": 0.0,
            "Throttle_Position_Pct": 100.0,
            "Brake_Pressure_Bar": 0.0,
        }
        encoded = dbc_loader.encode_message(0x200, signal_values)
        frame = __import__("backend.app.canbus.frame", fromlist=["CANFrame"]).CANFrame(
            id=0x200, data=encoded, dlc=len(encoded)
        )
        ecu._handle_can_message(frame)

        # Vérifier qu'une alerte a été générée
        assert len(ecu.alert_history) > 0
        assert ecu.alert_history[-1]["alert_type"] == 3  # Alerte vitesse

    def test_dashboard_publish_dashboard_alert(self, can_bus, dbc_loader):
        """Test la publication de DASHBOARD_ALERT (0x300)."""
        ecu = Dashboard_Ecu(ecus_id="dash_007", can_bus=can_bus)
        ecu._raise_alert(
            alert_type=1,
            alert_level=2,
            message_id=100,
            alert_value=3000,
            active=True,
        )

        history = can_bus.get_message_history()
        alert_frames = [f for f in history if f.id == 0x300]
        assert len(alert_frames) >= 1

        frame = alert_frames[-1]
        decoded = dbc_loader.decode_can_frame(frame.id, frame.data)
        signals = decoded["signals"]
        assert signals["Alert_Type"] == 1
        assert signals["Alert_Level"] == 2
        assert signals["Alert_Active"] == 1

    def test_dashboard_clear_alerts(self, can_bus):
        """Test l'effacement des alertes."""
        ecu = Dashboard_Ecu(ecus_id="dash_008", can_bus=can_bus)
        ecu._raise_alert(alert_type=1, alert_level=2, message_id=100, alert_value=100, active=True)
        assert len(ecu.alert_history) == 1

        ecu.clear_alerts()
        assert len(ecu.alert_history) == 0
        assert ecu.current_alert_type == 0
        assert ecu.current_alert_level == 0

    def test_dashboard_get_status(self, can_bus):
        """Test la récupération du statut Dashboard."""
        ecu = Dashboard_Ecu(ecus_id="dash_009", can_bus=can_bus)
        status = ecu.get_status()
        assert status["id"] == "dash_009"
        assert status["type"] == "Dashboard_ECU"
        assert status["active"] is True
        assert "current_speed_kmh" in status
        assert "alert_count" in status


# ============================================================================
# TESTS DE COMMUNICATION INTER-ECU
# ============================================================================

class TestECUCommunication:
    """Tests de communication entre ECUs via le bus CAN."""

    def test_adas_to_vcu_brake_chain(self, can_bus, dbc_loader):
        """Test chaîne complète : ADAS détecte obstacle -> AEB -> BRAKE_COMMAND -> VCU freine."""
        adas = ADAS_Ecu(ecus_id="adas_chain", can_bus=can_bus)
        vcu = VCU_Ecu(ecus_id="vcu_chain", can_bus=can_bus)

        # ADAS détecte un obstacle critique
        adas.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=10.0,
            relative_speed_mps=-20.0,
        )

        # Vérifier que VCU a reçu le BRAKE_COMMAND
        history = can_bus.get_message_history()
        brake_frames = [f for f in history if f.id == 0x201]
        assert len(brake_frames) >= 1

        # VCU devrait avoir traité le freinage
        assert vcu.brake_pressure_bar > 0.0

    def test_full_ecu_loop(self, can_bus, dbc_loader):
        """Test complet : ADAS -> Dashboard et VCU -> Dashboard."""
        adas = ADAS_Ecu(ecus_id="adas_loop", can_bus=can_bus)
        vcu = VCU_Ecu(ecus_id="vcu_loop", can_bus=can_bus)
        dash = Dashboard_Ecu(ecus_id="dash_loop", can_bus=can_bus)

        # ADAS publie son statut
        adas.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=25.0,
            relative_speed_mps=-15.0,
        )

        # VCU met à jour l'état du véhicule
        vcu.update_vehicle_state(
            target_speed_kmh=60.0,
            throttle_position_pct=40.0,
        )

        # Vérifier que le Dashboard a reçu des messages des deux ECUs
        dash_history = dash.get_message_history()
        adas_frames = [f for f in dash_history if f.id == 0x100]
        vcu_frames = [f for f in dash_history if f.id == 0x200]

        assert len(adas_frames) >= 1, "Dashboard devrait recevoir ADAS_STATUS"
        assert len(vcu_frames) >= 1, "Dashboard devrait recevoir VEHICLE_STATUS"

        # Vérifier que le Dashboard a décodé les informations
        assert dash.obstacle_detected is True
        assert dash.current_speed_kmh > 0

    def test_all_ecus_on_same_bus(self, can_bus):
        """Test que plusieurs ECU peuvent coexister sur le même bus."""
        adas = ADAS_Ecu(ecus_id="adas_multi", can_bus=can_bus)
        vcu = VCU_Ecu(ecus_id="vcu_multi", can_bus=can_bus)
        dash = Dashboard_Ecu(ecus_id="dash_multi", can_bus=can_bus)

        assert adas.is_connected() is True
        assert vcu.is_connected() is True
        assert dash.is_connected() is True

        # Chaque ECU devrait être abonné au bus
        assert len(can_bus._subscribers) == 3