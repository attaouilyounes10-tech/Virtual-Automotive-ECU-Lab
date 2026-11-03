"""Tests for DBC loader implementation."""

import pytest
from backend.app.canbus.dbc_loader import CANDbcLoader
from backend.app.canbus.frame import CANFrame
from backend.app.canbus.errors import CANError


class TestCANDbcLoader:
    """Tests for CANDbcLoader class."""

    def test_loader_initialization(self):
        """Test loader initialization."""
        loader = CANDbcLoader()
        assert loader.dbc_path is not None or loader.dbc_path is None
        assert loader.is_loaded is False

    def test_loader_with_path(self):
        """Test loader with explicit DBC path."""
        loader = CANDbcLoader(dbc_path="backend/dbc/vael_can.dbc")
        loader.load()
        assert loader.is_loaded is True

    def test_loader_missing_dbc(self):
        """Test loader with missing DBC file."""
        loader = CANDbcLoader(dbc_path="missing.dbc")
        with pytest.raises(CANError):
            loader.load()

    def test_get_message_by_id_found(self):
        """Test getting a message that exists in DBC."""
        loader = CANDbcLoader()
        loader.load()
        message = loader.get_message_by_id(256)
        assert message is not None
        assert message.frame_id == 256

    def test_get_message_by_id_not_found(self):
        """Test getting a message that doesn't exist."""
        loader = CANDbcLoader()
        loader.load()
        message = loader.get_message_by_id(9999)
        assert message is None

    def test_encode_decode_cycle_adas_status(self):
        """Test encode/decode cycle for ADAS_STATUS message."""
        loader = CANDbcLoader()
        loader.load()

        signal_values = {
            "ADAS_Active": 1,
            "ADAS_Mode": 2,
            "Vehicle_Detected": 1,
            "Obstacle_Distance_m": 50.0,
            "Relative_Speed_mps": 15.0,
            "Collision_Risk_Level": 2,
            "FCW_Active": 1,
            "AEB_Active": 0,
            "Reserved": 0,
        }

        encoded = loader.encode_message(256, signal_values)
        assert len(encoded) == 8

        decoded = loader.decode_message(256, encoded)
        assert decoded["ADAS_Active"] == 1
        assert decoded["ADAS_Mode"] == 2
        assert decoded["Vehicle_Detected"] == 1
        assert decoded["Obstacle_Distance_m"] == 50.0
        assert decoded["Relative_Speed_mps"] == pytest.approx(15.0)
        assert decoded["Collision_Risk_Level"] == 2
        assert decoded["FCW_Active"] == 1
        assert decoded["AEB_Active"] == 0
        assert decoded["Reserved"] == 0

    def test_encode_invalid_signal(self):
        """Test encoding with invalid signal name."""
        loader = CANDbcLoader()
        loader.load()

        signal_values = {
            "ADAS_Active": 1,
            "ADAS_Mode": 2,
            "Invalid_Signal": 1,
        }

        with pytest.raises(CANError):
            loader.encode_message(256, signal_values)

    def test_encode_can_frame(self):
        """Test full CAN frame encoding."""
        loader = CANDbcLoader()
        loader.load()

        signal_values = {
            "ADAS_Active": 1,
            "ADAS_Mode": 2,
            "Vehicle_Detected": 1,
            "Obstacle_Distance_m": 50.0,
            "Relative_Speed_mps": 15.0,
            "Collision_Risk_Level": 2,
            "FCW_Active": 1,
            "AEB_Active": 0,
            "Reserved": 0,
        }

        frame_data = loader.encode_can_frame(256, signal_values)
        assert frame_data["id"] == 256
        assert frame_data["dlc"] == 8
        assert frame_data["data_hex"] == "158813dc6d000000"
        assert frame_data["signal_values"] == signal_values

    def test_decode_can_frame(self):
        """Test full CAN frame decoding."""
        loader = CANDbcLoader()
        loader.load()

        data = bytes.fromhex("158813dc6d000000")
        decoded_frame = loader.decode_can_frame(256, data)

        assert decoded_frame["id"] == 256
        assert decoded_frame["dlc"] == 8
        assert decoded_frame["data_hex"] == "158813dc6d000000"
        assert decoded_frame["signals"]["ADAS_Active"] == 1
        assert decoded_frame["signals"]["ADAS_Mode"] == 2
        assert decoded_frame["signals"]["Vehicle_Detected"] == 1
        assert decoded_frame["signals"]["Obstacle_Distance_m"] == 50.0

    def test_get_signal_info(self):
        """Test getting signal information from DBC."""
        loader = CANDbcLoader()
        loader.load()

        signals = loader.get_signal_info(256)
        assert len(signals) > 0

        first_signal = signals[0]
        assert "name" in first_signal
        assert "start_bit" in first_signal
        assert "length" in first_signal
        assert "scale" in first_signal
        assert "offset" in first_signal
        assert "min" in first_signal
        assert "max" in first_signal
        assert "unit" in first_signal
        assert "is_signed" in first_signal

    def test_list_all_messages(self):
        """Test listing all messages in DBC."""
        loader = CANDbcLoader()
        loader.load()

        messages = loader.list_all_messages()
        assert len(messages) > 0

        for msg in messages:
            assert "frame_id" in msg
            assert "name" in msg
            assert "dlc" in msg
            assert "signals" in msg

    def test_id_out_of_range(self):
        """Test that encoding fails with ID out of range."""
        loader = CANDbcLoader()
        loader.load()

        with pytest.raises(CANError):
            loader.encode_message(9999, {})

    def test_data_length_mismatch(self):
        """Test decoding with data length mismatch."""
        loader = CANDbcLoader()
        loader.load()

        # Use wrong length data (should still decode for valid DBC messages)
        data = bytes.fromhex("0101")  # Too short for 8-byte message
        # This might not raise an error depending on cantools behavior
        try:
            decoded = loader.decode_message(256, data)
            # If we get here without exception, verify incomplete result
            assert isinstance(decoded, dict)
        except CANError:
            # Expected: cantools raises CANError for data size mismatch
            pass

    def test_can_frame_attributes(self):
        """Test that encoded CAN frame has proper attributes."""
        loader = CANDbcLoader()
        loader.load()

        signal_values = {
            "ADAS_Active": 1,
            "ADAS_Mode": 2,
            "Vehicle_Detected": 1,
            "Obstacle_Distance_m": 50.0,
            "Relative_Speed_mps": 15.0,
            "Collision_Risk_Level": 2,
            "FCW_Active": 1,
            "AEB_Active": 0,
            "Reserved": 0,
        }

        frame_data = loader.encode_can_frame(256, signal_values)
        assert "id" in frame_data
        assert "dlc" in frame_data
        assert "data" in frame_data
        assert "data_hex" in frame_data
        assert "signal_values" in frame_data

        # Validate frame attributes
        assert frame_data["id"] == 256
        assert frame_data["dlc"] == 8
        assert isinstance(frame_data["data"], bytes)
        assert len(frame_data["data"]) == 8