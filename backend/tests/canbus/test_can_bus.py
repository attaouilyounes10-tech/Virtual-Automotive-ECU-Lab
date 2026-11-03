"""Tests for CAN bus implementation."""

import pytest
from backend.app.canbus.bus import CANBus
from backend.app.canbus.frame import CANFrame
from backend.app.canbus.subscriber import CANSubscriber
from backend.app.canbus.errors import CANError, CANInvalidIdentifierError, CANInvalidDLCError, CANInvalidPayloadError


class TestCANBus:
    """Tests for CANBus class."""

    def test_bus_initialization(self):
        """Test initialization of CAN bus."""
        bus = CANBus("virtual_can")
        assert bus.bus_name == "virtual_can"
        assert len(bus.get_subscribers()) == 0
        assert bus.get_message_count() == 0

    def test_add_remove_subscriber(self):
        """Test adding and removing subscribers."""
        bus = CANBus()
        subscriber = CANSubscriber("test_subscriber")
        bus.add_subscriber(subscriber)
        assert len(bus.get_subscribers()) == 1

        bus.remove_subscriber("test_subscriber")
        assert len(bus.get_subscribers()) == 0

    def test_publish_valid_frame(self):
        """Test publishing a valid CAN frame."""
        bus = CANBus()
        frame = CANFrame(id=0x100, data=b"\x01\x02\x03\x04", dlc=4)
        result = bus.publish(frame)
        assert result is True
        assert bus.get_message_count() == 1

    def test_publish_invalid_frame_due_to_id(self):
        """Test that creating a frame with invalid ID raises error."""
        with pytest.raises(CANInvalidIdentifierError):
            CANFrame(id=0x800, data=b"\x01", dlc=1)  # ID too large

    def test_publish_invalid_frame_due_to_dlc(self):
        """Test that creating a frame with invalid DLC raises error."""
        with pytest.raises(CANInvalidDLCError):
            CANFrame(id=0x100, data=b"\x01", dlc=9)  # DLC > 8

    def test_publish_invalid_frame_due_to_data_length(self):
        """Test that creating a frame with data longer than DLC raises error."""
        with pytest.raises(CANInvalidPayloadError):
            CANFrame(id=0x100, data=b"\x01\x02\x03\x04\x05", dlc=4)  # 5 bytes but DLC=4

    def test_publish_frame_with_history(self):
        """Test that frames are stored in history."""
        bus = CANBus()
        frame1 = CANFrame(id=0x100, data=b"\x01", dlc=1)
        frame2 = CANFrame(id=0x101, data=b"\x02", dlc=1)

        bus.publish(frame1)
        bus.publish(frame2)

        history = bus.get_message_history()
        assert len(history) == 2
        assert history[0].id == 0x100
        assert history[1].id == 0x101

    def test_get_message_history_with_filter(self):
        """Test filtering message history."""
        bus = CANBus()
        frame1 = CANFrame(id=0x100, data=b"\x01", dlc=1)
        frame2 = CANFrame(id=0x101, data=b"\x02", dlc=1)
        frame3 = CANFrame(id=0x102, data=b"\x03", dlc=1)

        bus.publish(frame1)
        bus.publish(frame2)
        bus.publish(frame3)

        # Filter by ID
        filtered = bus.get_message_history({"can_id": 0x100})
        assert len(filtered) == 1
        assert filtered[0].id == 0x100

    def test_get_message_history_with_timestamp_filter(self):
        """Test filtering history by time range."""
        bus = CANBus()
        frame1 = CANFrame(id=0x100, data=b"\x01", dlc=1)
        frame2 = CANFrame(id=0x101, data=b"\x02", dlc=1)

        # Simulate time difference
        frame1.timestamp = 1000.0
        frame2.timestamp = 2000.0

        bus.publish(frame1)
        bus.publish(frame2)

        # Filter by time range
        filtered = bus.get_message_history({"timestamp_min": 1500.0, "timestamp_max": 2500.0})
        assert len(filtered) == 1
        assert filtered[0].id == 0x101

    def test_bus_error_handling(self):
        """Test that bus errors are properly tracked."""
        bus = CANBus()
        bus.set_bus_error(CANError("Test error"))
        assert bus.get_bus_error() is not None

    def test_subscriber_callback_invocation(self):
        """Test that subscriber callbacks are called."""
        received = {"frame": None}

        def capture_callback(frame):
            received["frame"] = frame

        subscriber = CANSubscriber("test_sub", callback=capture_callback)
        bus = CANBus()
        bus.add_subscriber(subscriber)

        frame = CANFrame(id=0x100, data=b"\x01", dlc=1)
        bus.publish(frame)

        # Callback is synchronous, no need to wait
        assert received["frame"] is not None
        assert received["frame"].id == 0x100
        assert len(bus.get_subscribers()) == 1  # Subscriber still exists