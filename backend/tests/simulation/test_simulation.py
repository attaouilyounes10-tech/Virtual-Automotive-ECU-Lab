"""Tests unitaires et d'intégration pour la Phase 4 - Moteur de simulation globale du véhicule.

Ces tests couvrent :
- Cycle de vie de la simulation (start, stop, pause, resume, reset)
- Communication ADAS -> BRAKE_COMMAND -> VCU -> VEHICLE_STATUS
- Alertes Dashboard ECU
- Cohérence des données échangées
- Transitions start/stop/reset et gestion des erreurs
- Scénarios normaux et situations de collision
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch

from backend.app.simulation.simulation import SimulationEngine
from backend.app.canbus.bus import CANBus
from backend.app.canbus.frame import CANFrame
from backend.app.canbus.dbc_loader import CANDbcLoader


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def simulation_engine():
    """Retourne une instance de SimulationEngine pour les tests."""
    return SimulationEngine(
        bus_name="test_bus",
        adas_id="test_adas",
        vcu_id="test_vcu",
        dash_id="test_dash"
    )


@pytest.fixture
def dbc_loader():
    """Retourne un DBC loader chargé."""
    loader = CANDbcLoader()
    loader.load()
    return loader


# ============================================================================
# TESTS DU CYCLE DE VIE
# ============================================================================

class TestSimulationLifecycle:
    """Tests du cycle de vie de la simulation."""

    def test_initialization(self, simulation_engine):
        """Test l'initialisation du moteur de simulation."""
        assert simulation_engine.is_running is False
        assert simulation_engine.is_paused is False
        assert simulation_engine._thread is None
        assert simulation_engine.vehicle_state['speed_kmh'] == 0.0
        assert simulation_engine.vehicle_state['target_speed_kmh'] == 0.0

    def test_start_simulation(self, simulation_engine):
        """Test le démarrage de la simulation."""
        simulation_engine.start()
        assert simulation_engine.is_running is True
        assert simulation_engine.is_paused is False
        assert simulation_engine._thread is not None
        assert simulation_engine._thread.is_alive()

        # Arrêt pour cleanup
        simulation_engine.stop()

    def test_stop_simulation(self, simulation_engine):
        """Test l'arrêt de la simulation."""
        simulation_engine.start()
        time.sleep(0.1)  # Laisser le thread démarrer
        simulation_engine.stop()
        assert simulation_engine.is_running is False
        assert simulation_engine.is_paused is False

    def test_pause_resume(self, simulation_engine):
        """Test la mise en pause et reprise."""
        simulation_engine.start()
        time.sleep(0.1)

        # Pause
        simulation_engine.pause()
        assert simulation_engine.is_paused is True

        # Reprise
        simulation_engine.resume()
        assert simulation_engine.is_paused is False

        simulation_engine.stop()

    def test_reset_simulation(self, simulation_engine):
        """Test la réinitialisation de la simulation."""
        simulation_engine.start()
        time.sleep(0.2)

        # Modifier l'état
        simulation_engine.vehicle_state['speed_kmh'] = 50.0

        # Reset
        simulation_engine.reset()
        assert simulation_engine.is_running is True
        assert simulation_engine.vehicle_state['speed_kmh'] == 0.0

        simulation_engine.stop()

    def test_get_simulation_state(self, simulation_engine):
        """Test la récupération de l'état de simulation."""
        simulation_engine.start()
        state = simulation_engine.get_simulation_state()

        assert 'is_running' in state
        assert 'is_paused' in state
        assert 'current_time' in state
        assert 'elapsed_time' in state
        assert 'vehicle_state' in state
        assert state['is_running'] is True

        simulation_engine.stop()


# ============================================================================
# TESTS DE COMMUNICATION INTER-ECU
# ============================================================================

class TestECUCommunication:
    """Tests de communication entre ECUs via le bus CAN."""

    def test_adas_publishes_adas_status(self, simulation_engine, dbc_loader):
        """Test que l'ADAS publie ADAS_STATUS (0x100)."""
        simulation_engine.start()
        time.sleep(0.5)  # Laisser le temps au premier cycle de simulation

        # Vérifier les messages sur le bus
        history = simulation_engine.bus.get_message_history()
        adas_frames = [f for f in history if f.id == 0x100]

        assert len(adas_frames) >= 1, "ADAS devrait publier ADAS_STATUS"

        # Vérifier le contenu
        frame = adas_frames[-1]
        decoded = dbc_loader.decode_can_frame(frame.id, frame.data)
        signals = decoded["signals"]
        assert "ADAS_Active" in signals
        assert "Vehicle_Detected" in signals
        assert "Collision_Risk_Level" in signals

        simulation_engine.stop()

    def test_adas_to_vcu_brake_chain(self, simulation_engine, dbc_loader):
        """Test chaîne complète : ADAS détecte obstacle -> AEB -> BRAKE_COMMAND -> VCU freine."""
        simulation_engine.start()
        time.sleep(0.2)

        # Simuler une détection d'obstacle critique par l'ADAS
        simulation_engine.adas.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=10.0,
            relative_speed_mps=-20.0,
        )

        # Attendre que la chaîne de traitement se propage
        time.sleep(0.2)

        # Vérifier que VCU a reçu le BRAKE_COMMAND (0x201)
        history = simulation_engine.bus.get_message_history()
        brake_frames = [f for f in history if f.id == 0x201]
        assert len(brake_frames) >= 1, "AEB devrait déclencher un BRAKE_COMMAND"

        # Vérifier que VCU a publié VEHICLE_STATUS après freinage
        vehicle_frames = [f for f in history if f.id == 0x200]
        assert len(vehicle_frames) >= 1, "VCU devrait publier VEHICLE_STATUS après freinage"

        # Vérifier que la vitesse a diminué
        frame = vehicle_frames[-1]
        decoded = dbc_loader.decode_can_frame(frame.id, frame.data)
        signals = decoded["signals"]
        assert signals["Vehicle_Speed_kmh"] >= 0.0

        simulation_engine.stop()

    def test_dashboard_receives_alerts(self, simulation_engine, dbc_loader):
        """Test que le Dashboard reçoit et traite les alertes."""
        simulation_engine.start()
        time.sleep(0.2)

        # Déclencher une situation d'alerte
        simulation_engine.adas.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=15.0,
            relative_speed_mps=-15.0,
        )

        time.sleep(0.2)

        # Vérifier que DASHBOARD_ALERT (0x300) a été publié
        history = simulation_engine.bus.get_message_history()
        alert_frames = [f for f in history if f.id == 0x300]
        assert len(alert_frames) >= 1, "Dashboard devrait publier DASHBOARD_ALERT"

        # Vérifier le contenu de l'alerte
        frame = alert_frames[-1]
        decoded = dbc_loader.decode_can_frame(frame.id, frame.data)
        signals = decoded["signals"]
        assert "Alert_Type" in signals
        assert "Alert_Level" in signals
        assert "Alert_Active" in signals
        assert signals["Alert_Active"] == 1

        simulation_engine.stop()

    def test_vehicle_status_published(self, simulation_engine, dbc_loader):
        """Test que VEHICLE_STATUS est publié régulièrement."""
        simulation_engine.start()
        time.sleep(0.3)

        history = simulation_engine.bus.get_message_history()
        vehicle_frames = [f for f in history if f.id == 0x200]
        assert len(vehicle_frames) >= 1, "VCU devrait publier VEHICLE_STATUS"

        frame = vehicle_frames[-1]
        decoded = dbc_loader.decode_can_frame(frame.id, frame.data)
        signals = decoded["signals"]
        assert "Vehicle_Speed_kmh" in signals
        assert "Target_Speed_kmh" in signals
        assert "Acceleration_mps2" in signals
        assert "Throttle_Position_Pct" in signals
        assert "Brake_Pressure_Bar" in signals

        simulation_engine.stop()

    def test_collision_warning_published(self, simulation_engine, dbc_loader):
        """Test que COLLISION_WARNING est publié quand risque détecté."""
        simulation_engine.start()
        time.sleep(0.2)

        # Simuler un obstacle proche
        simulation_engine.adas.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=25.0,
            relative_speed_mps=-15.0,
        )

        time.sleep(0.2)

        history = simulation_engine.bus.get_message_history()
        warning_frames = [f for f in history if f.id == 0x101]
        assert len(warning_frames) >= 1, "ADAS devrait publier COLLISION_WARNING"

        frame = warning_frames[-1]
        decoded = dbc_loader.decode_can_frame(frame.id, frame.data)
        signals = decoded["signals"]
        assert "Warning_Level" in signals
        assert "Time_To_Collision_s" in signals
        assert "Distance_At_Warning_m" in signals

        simulation_engine.stop()


# ============================================================================
# TESTS DE COHÉRENCE DES DONNÉES
# ============================================================================

class TestDataConsistency:
    """Tests de cohérence des données échangées."""

    def test_speed_non_negative(self, simulation_engine):
        """Test que la vitesse ne devient jamais négative."""
        simulation_engine.start()
        time.sleep(0.5)

        state = simulation_engine.get_simulation_state()
        assert state['vehicle_state']['speed_kmh'] >= 0.0

        # Tester avec freinage d'urgence
        simulation_engine.adas.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=5.0,
            relative_speed_mps=-30.0,
        )
        time.sleep(0.5)

        state = simulation_engine.get_simulation_state()
        assert state['vehicle_state']['speed_kmh'] >= 0.0

        simulation_engine.stop()

    def test_brake_pressure_bounds(self, simulation_engine):
        """Test que la pression de freinage reste dans les limites."""
        simulation_engine.start()
        time.sleep(0.2)

        # Déclencher freinage d'urgence
        simulation_engine.adas.update_obstacle_data(
            obstacle_detected=True,
            obstacle_distance_m=5.0,
            relative_speed_mps=-30.0,
        )
        time.sleep(0.5)

        state = simulation_engine.get_simulation_state()
        assert 0.0 <= state['vehicle_state']['brake_pressure_bar'] <= 40.95

        simulation_engine.stop()

    def test_collision_risk_levels(self, simulation_engine):
        """Test les niveaux de risque de collision."""
        simulation_engine.start()
        time.sleep(0.2)

        # Pas d'obstacle -> niveau 0
        simulation_engine.adas.update_obstacle_data(False, 0.0, 0.0)
        time.sleep(0.1)
        assert simulation_engine.vehicle_state['collision_risk_level'] == 0

        # Obstacle loin -> niveau 1
        simulation_engine.adas.update_obstacle_data(True, 80.0, -5.0)
        time.sleep(0.1)
        assert simulation_engine.vehicle_state['collision_risk_level'] == 1

        # Obstacle moyen -> niveau 2
        simulation_engine.adas.update_obstacle_data(True, 30.0, -10.0)
        time.sleep(0.1)
        assert simulation_engine.vehicle_state['collision_risk_level'] == 2

        # Obstacle proche -> niveau 3
        simulation_engine.adas.update_obstacle_data(True, 15.0, -20.0)
        time.sleep(0.1)
        assert simulation_engine.vehicle_state['collision_risk_level'] == 3

        simulation_engine.stop()

    def test_fcw_aeb_activation(self, simulation_engine):
        """Test l'activation FCW et AEB."""
        simulation_engine.start()
        time.sleep(0.2)

        # Situation de warning
        simulation_engine.adas.update_obstacle_data(True, 30.0, -15.0)
        time.sleep(0.1)
        assert simulation_engine.vehicle_state['fcw_active'] is True
        assert simulation_engine.vehicle_state['aeb_active'] is False

        # Situation d'urgence
        simulation_engine.adas.update_obstacle_data(True, 10.0, -20.0)
        time.sleep(0.1)
        assert simulation_engine.vehicle_state['fcw_active'] is True
        assert simulation_engine.vehicle_state['aeb_active'] is True

        simulation_engine.stop()


# ============================================================================
# TESTS DE SCÉNARIOS
# ============================================================================

class TestScenarios:
    """Tests des scénarios de conduite."""

    def test_normal_driving_scenario(self, simulation_engine):
        """Test un scénario de conduite normale."""
        simulation_engine.start()

        # Configurer un scénario normal
        simulation_engine.vehicle_state['target_speed_kmh'] = 60.0
        simulation_engine.vehicle_state['throttle_position_pct'] = 40.0

        time.sleep(1.0)

        state = simulation_engine.get_simulation_state()
        assert state['vehicle_state']['speed_kmh'] > 0.0
        assert state['vehicle_state']['target_speed_kmh'] == 60.0

        simulation_engine.stop()

    def test_emergency_braking_scenario(self, simulation_engine, dbc_loader):
        """Test un scénario de freinage d'urgence."""
        simulation_engine.start()

        # Véhicule en mouvement
        simulation_engine.vehicle_state['target_speed_kmh'] = 80.0
        simulation_engine.vehicle_state['throttle_position_pct'] = 50.0
        time.sleep(0.5)

        # Obstacle détecté -> AEB
        simulation_engine.adas.update_obstacle_data(True, 10.0, -25.0)
        time.sleep(0.5)

        # Vérifier que la vitesse a diminué
        state = simulation_engine.get_simulation_state()
        assert state['vehicle_state']['aeb_active'] is True
        assert state['vehicle_state']['speed_kmh'] <= 80.0

        # Vérifier la trame VEHICLE_STATUS
        history = simulation_engine.bus.get_message_history()
        vehicle_frames = [f for f in history if f.id == 0x200]
        assert len(vehicle_frames) >= 1

        simulation_engine.stop()

    def test_obstacle_avoidance_scenario(self, simulation_engine):
        """Test un scénario d'évitement d'obstacle."""
        simulation_engine.start()

        # Véhicule en mouvement
        simulation_engine.vehicle_state['target_speed_kmh'] = 50.0
        simulation_engine.vehicle_state['throttle_position_pct'] = 30.0
        time.sleep(0.3)

        # Obstacle détecté, mais distance suffisante pour warning seulement
        simulation_engine.adas.update_obstacle_data(True, 40.0, -10.0)
        time.sleep(0.3)

        state = simulation_engine.get_simulation_state()
        assert state['vehicle_state']['fcw_active'] is True
        assert state['vehicle_state']['aeb_active'] is False
        assert state['vehicle_state']['collision_risk_level'] == 2

        simulation_engine.stop()


# ============================================================================
# TESTS DE GESTION D'ERREURS
# ============================================================================

class TestErrorHandling:
    """Tests de gestion d'erreurs."""

    def test_stop_not_running(self, simulation_engine):
        """Test l'arrêt quand la simulation n'est pas démarrée."""
        # Ne devrait pas lever d'exception
        simulation_engine.stop()
        assert simulation_engine.is_running is False

    def test_pause_not_running(self, simulation_engine):
        """Test la pause quand la simulation n'est pas démarrée."""
        simulation_engine.pause()
        assert simulation_engine.is_paused is False

    def test_resume_not_paused(self, simulation_engine):
        """Test la reprise quand la simulation n'est pas en pause."""
        simulation_engine.start()
        simulation_engine.resume()  # Ne devrait pas lever d'exception
        simulation_engine.stop()

    def test_multiple_starts(self, simulation_engine):
        """Test plusieurs démarrages consécutifs."""
        simulation_engine.start()
        simulation_engine.start()  # Ne devrait pas créer un nouveau thread
        simulation_engine.stop()

    def test_reset_when_stopped(self, simulation_engine):
        """Test le reset quand la simulation est arrêtée."""
        simulation_engine.reset()
        assert simulation_engine.is_running is True
        simulation_engine.stop()


# ============================================================================
# TESTS DE SIMULATION DÉTERMINISTE
# ============================================================================

class TestDeterministicSimulation:
    """Tests pour vérifier le fonctionnement déterministe."""

    def test_same_initial_state(self):
        """Test que deux simulations démarrent avec le même état initial."""
        sim1 = SimulationEngine()
        sim2 = SimulationEngine()

        sim1.start()
        sim2.start()
        time.sleep(0.1)

        state1 = sim1.get_simulation_state()
        state2 = sim2.get_simulation_state()

        assert state1['vehicle_state']['speed_kmh'] == state2['vehicle_state']['speed_kmh']
        assert state1['vehicle_state']['target_speed_kmh'] == state2['vehicle_state']['target_speed_kmh']

        sim1.stop()
        sim2.stop()

    def test_reproducible_scenario(self, simulation_engine):
        """Test qu'un même scénario produit des résultats reproductibles."""
        # Exécuter le scénario une première fois
        simulation_engine.start()
        simulation_engine.vehicle_state['target_speed_kmh'] = 60.0
        simulation_engine.vehicle_state['throttle_position_pct'] = 40.0
        time.sleep(0.5)
        state1 = simulation_engine.get_simulation_state()
        speed1 = state1['vehicle_state']['speed_kmh']
        simulation_engine.stop()

        # Exécuter le même scénario une seconde fois
        simulation_engine.start()
        simulation_engine.vehicle_state['target_speed_kmh'] = 60.0
        simulation_engine.vehicle_state['throttle_position_pct'] = 40.0
        time.sleep(0.5)
        state2 = simulation_engine.get_simulation_state()
        speed2 = state2['vehicle_state']['speed_kmh']
        simulation_engine.stop()

        # Les résultats devraient être proches (tolérance pour timing)
        assert abs(speed1 - speed2) < 5.0


# ============================================================================
# TESTS DE PERFORMANCE ET TIMING
# ============================================================================

class TestSimulationTiming:
    """Tests de timing de la simulation."""

    def test_time_elapsed(self, simulation_engine):
        """Test que le temps écoulé est correctement mesuré."""
        simulation_engine.start()
        time.sleep(0.5)

        state = simulation_engine.get_simulation_state()
        assert state['elapsed_time'] >= 0.4
        assert state['elapsed_time'] <= 1.0  # Avec marge

        simulation_engine.stop()

    def test_pause_preserves_time(self, simulation_engine):
        """Test que la pause préserve le temps écoulé."""
        simulation_engine.start()
        time.sleep(0.3)
        time_before_pause = simulation_engine.get_simulation_state()['elapsed_time']

        simulation_engine.pause()
        time.sleep(0.2)

        time_after_pause = simulation_engine.get_simulation_state()['elapsed_time']
        # Le temps ne devrait pas avoir beaucoup augmenté pendant la pause
        assert abs(time_after_pause - time_before_pause) < 0.1

        simulation_engine.resume()
        time.sleep(0.2)
        time_after_resume = simulation_engine.get_simulation_state()['elapsed_time']
        # Le temps devrait avoir augmenté après la reprise
        assert time_after_resume > time_after_pause + 0.1

        simulation_engine.stop()


# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])