"""Tests for CAN frame model."""

from __future__ import annotations
import pytest
from backend.app.canbus.frame import CANFrame
from backend.app.canbus.errors import (
    CANInvalidIdentifierError,
    CANInvalidDLCError,
    CANInvalidPayloadError,
)
from backend.app.core.constants import CAN_MAX_ID, CAN_MAX_DLC, CAN_MIN_DLC


class TestCANFrame:
    """Tests for CANFrame dataclass."""

    def test_valid_frame_creation(self):
        """Test creation of a valid CAN frame."""
        frame = CANFrame(id=0x100, data=b"\x01\x02\x03\x04\x05\x06\x07\x08", dlc=8)
        assert frame.id == 0x100
        assert frame.dlc == 8
        assert frame.data == b"\x01\x02\x03\x04\x05\x06\x07\x08"
        assert frame.is_standard is True
        assert frame.is_extended is False
        assert frame.timestamp is not None
        assert isinstance(frame.can_id_hex, str)

    def test_frame_id_hex_format(self):
        """Test CAN ID hexadecimal formatting."""
        frame = CANFrame(id=0x100, data=b"\x01", dlc=1)
        assert frame.can_id_hex == "0x100"

    def test_frame_data_padding(self):
        """Test that data is padded to DLC length."""
        frame = CANFrame(id=0x100, data=b"\x01\x02", dlc=4)
        assert frame.data == b"\x01\x02\x00\x00"
        assert len(frame.data) == 4

    def test_frame_id_at_minimum_boundary(self):
        """Test frame with ID 0 (minimum valid ID)."""
        frame = CANFrame(id=0, data=b"\x01", dlc=1)
        assert frame.id == 0

    def test_frame_id_at_maximum_boundary(self):
        """Test frame with ID at maximum 11-bit boundary."""
        frame = CANFrame(id=CAN_MAX_ID, data=b"\x01", dlc=1)
        assert frame.id == CAN_MAX_ID

    def test_frame_invalid_id_negative(self):
        """Test that negative CAN ID raises error."""
        with pytest.raises(CANInvalidIdentifierError):
            CANFrame(id=-1, data=b"\x01", dlc=1)

    def test_frame_invalid_id_too_large(self):
        """Test that CAN ID exceeding 11-bit range raises error."""
        with pytest.raises(CANInvalidIdentifierError):
            CANFrame(id=CAN_MAX_ID + 1, data=b"\x01", dlc=1)

    def test_frame_dlc_above_max(self):
        """Test that DLC above max raises error."""
        with pytest.raises(CANInvalidDLCError):
            CANFrame(id=0x100, data=b"\x01", dlc=CAN_MAX_DLC + 1)

    def test_frame_dlc_below_min(self):
        """Test that DLC below min raises error."""
        with pytest.raises(CANInvalidDLCError):
            CANFrame(id=0x100, data=b"\x01", dlc=CAN_MIN_DLC - 1)

    def test_frame_payload_longer_than_dlc(self):
        """Test that data longer than DLC raises error."""
        with pytest.raises(CANInvalidPayloadError):
            CANFrame(id=0x100, data=b"\x01\x02\x03\x04", dlc=2)

    def test_frame_data_longer_than_8_bytes(self):
        """Test that data exceeding 8 bytes raises error."""
        with pytest.raises(CANInvalidPayloadError):
            CANFrame(id=0x100, data=b"\x01\x02\x03\x04\x05\x06\x07\x08\x09", dlc=8)

    def test_frame_payload_hex_property(self):
        """Test payload hexadecimal string property."""
        frame = CANFrame(id=0x100, data=b"\x01\x02\x03", dlc=3)
        assert frame.payload_hex == "010203"

    def test_frame_default_timestamp(self):
        """Test that timestamp defaults to current time."""
        frame = CANFrame(id=0x100, data=b"\x01", dlc=1)
        assert frame.timestamp > 0
        assert isinstance(frame.timestamp, float)

    def test_frame_custom_timestamp(self):
        """Test custom timestamp assignment."""
        ts = 1234567890.0
        frame = CANFrame(id=0x100, data=b"\x01", dlc=1, timestamp=ts)
        assert frame.timestamp == ts

    def test_frame_str_representation(self):
        """Test human-readable string representation."""
        frame = CANFrame(id=0x100, data=b"\x01\x02", dlc=2)
        str_repr = str(frame)
        assert "0x100" in str_repr
        assert "0102" in str_repr

    def test_frame_encode_decode(self):
        """Test frame encode/decode cycle."""
        original = CANFrame(id=0x100, data=b"\x01\x02\x03\x04", dlc=4)
        encoded = original.encode()
        decoded = CANFrame.decode(encoded)
        assert decoded.id == original.id
        assert decoded.data == original.data
        assert decoded.dlc == original.dlc

    def test_frame_dlc_zero(self):
        """Test frame with DLC 0 (no data)."""
        frame = CANFrame(id=0x100, data=b"", dlc=0)
        assert frame.dlc == 0
        assert frame.data == b""