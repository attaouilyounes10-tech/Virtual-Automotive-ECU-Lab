"""Tests for CAN subscriber implementation."""

import pytest
from backend.app.canbus.subscriber import CANSubscriber
from backend.app.canbus.frame import CANFrame
from backend.app.canbus.errors import CANError
from backend.app.canbus.bus import CANBus
from backend.app.canbus.filter import CANMessageFilterBuilder


class TestCANSubscriber:
    """Tests for CANSubscriber class."""

    def test_subscriber_creation(self):
        """Test basic subscriber creation."""
        subscriber = CANSubscriber("test_sub")
        assert subscriber.subscriber_id == "test_sub"
        assert subscriber.callback is None
        assert subscriber.filter is None
        assert subscriber.message_count == 0
        assert subscriber.is_active is False

    def test_subscriber_with_callback(self):
        """Test subscriber with callback function."""
        def capture_callback(frame):
            capture_callback.called = True
            capture_callback.last_frame = frame

        subscriber = CANSubscriber("test_sub", callback=capture_callback)
        assert subscriber.callback is not None

    def test_subscriber_without_callback(self):
        """Test subscriber without callback."""
        subscriber = CANSubscriber("test_sub")
        assert subscriber.callback is None

    def test_subscriber_filter_matching(self):
        """Test subscriber with filter criteria."""
        filter_criteria = {"can_id": 0x100}
        subscriber = CANSubscriber("test_sub", filter_criteria=filter_criteria)
        assert subscriber.filter == filter_criteria

    def test_subscriber_filter_none(self):
        """Test subscriber without filter."""
        subscriber = CANSubscriber("test_sub")
        assert subscriber.filter is None

    def test_subscriber_receive_without_filter(self):
        """Test subscriber receiving frame without filter."""
        received_frames = []

        def callback(frame):
            received_frames.append(frame)

        subscriber = CANSubscriber("test_sub", callback=callback)
        frame = CANFrame(id=0x100, data=b"\x01", dlc=1)
        subscriber.receive(frame)

        assert len(received_frames) == 1
        assert received_frames[0].id == 0x100
        assert subscriber.message_count == 1
        assert subscriber.is_active is True

    def test_subscriber_receive_with_filter_match(self):
        """Test subscriber receiving matching frame."""
        received_frames = []

        def callback(frame):
            received_frames.append(frame)

        filter_criteria = {"can_id": 0x100}
        subscriber = CANSubscriber("test_sub", callback=callback, filter_criteria=filter_criteria)
        frame1 = CANFrame(id=0x100, data=b"\x01", dlc=1)  # Should match
        frame2 = CANFrame(id=0x101, data=b"\x02", dlc=1)  # Should not match

        subscriber.receive(frame1)
        subscriber.receive(frame2)

        assert len(received_frames) == 1
        assert received_frames[0].id == 0x100
        assert subscriber.message_count == 1

    def test_subscriber_receive_with_filter_no_match(self):
        """Test subscriber receiving non-matching frame."""
        received_frames = []

        def callback(frame):
            received_frames.append(frame)

        filter_criteria = {"can_id": 0x101}
        subscriber = CANSubscriber("test_sub", callback=callback, filter_criteria=filter_criteria)
        frame = CANFrame(id=0x100, data=b"\x01", dlc=1)

        subscriber.receive(frame)
        assert len(received_frames) == 0
        assert subscriber.message_count == 0

    def test_subscriber_receive_with_can_message_filter(self):
        """Test subscriber using CANMessageFilter."""
        received_frames = []

        def callback(frame):
            received_frames.append(frame)

        filter_obj = CANMessageFilterBuilder().with_can_id(0x100).build()
        subscriber = CANSubscriber("test_sub", callback=callback, filter_criteria=filter_obj)

        frame1 = CANFrame(id=0x100, data=b"\x01", dlc=1)  # Should match
        frame2 = CANFrame(id=0x101, data=b"\x02", dlc=1)  # Should not match

        subscriber.receive(frame1)
        subscriber.receive(frame2)

        assert len(received_frames) == 1
        assert received_frames[0].id == 0x100

    def test_subscriber_history_storage(self):
        """Test that subscriber stores frame history."""
        subscriber = CANSubscriber("test_sub")
        frame1 = CANFrame(id=0x100, data=b"\x01", dlc=1)
        frame2 = CANFrame(id=0x101, data=b"\x02", dlc=1)

        subscriber.receive(frame1)
        subscriber.receive(frame2)

        assert len(subscriber.frame_history) == 2
        assert subscriber.frame_history[0].id == 0x100
        assert subscriber.frame_history[1].id == 0x101

    def test_subscriber_history_limit(self):
        """Test that subscriber history is limited."""
        subscriber = CANSubscriber("test_sub")
        subscriber._max_history = 3  # Override for testing

        for i in range(5):
            frame = CANFrame(id=0x100 + i, data=bytes([i]), dlc=1)
            subscriber.receive(frame)

        assert len(subscriber.frame_history) == 3
        assert subscriber.frame_history[0].id == 0x102
        assert subscriber.frame_history[1].id == 0x103
        assert subscriber.frame_history[2].id == 0x104

    def test_subscriber_clear_history(self):
        """Test clearing subscriber history."""
        subscriber = CANSubscriber("test_sub")
        frame = CANFrame(id=0x100, data=b"\x01", dlc=1)
        subscriber.receive(frame)

        assert subscriber.message_count == 1
        assert len(subscriber.frame_history) == 1

        subscriber.clear_history()
        assert subscriber.message_count == 0
        assert subscriber.frame_history == []

    def test_subscriber_frame_timestamp_tracking(self):
        """Test that subscriber tracks frame timestamps."""
        subscriber = CANSubscriber("test_sub")
        initial_ts = subscriber.last_message_time
        frame = CANFrame(id=0x100, data=b"\x01", dlc=1)
        subscriber.receive(frame)

        assert subscriber.last_message_time is not None
        # Handle case where initial_ts is None
        if initial_ts is None:
            assert subscriber.last_message_time > 0
        else:
            assert subscriber.last_message_time > initial_ts

    def test_subscriber_set_callback_after_creation(self):
        """Test setting callback after subscriber creation."""
        subscriber = CANSubscriber("test_sub")

        def new_callback(frame):
            new_callback.called = True

        subscriber.set_callback(new_callback)
        assert subscriber.callback is not None

    def test_subscriber_set_filter_after_creation(self):
        """Test setting filter after subscriber creation."""
        subscriber = CANSubscriber("test_sub")
        filter_criteria = {"dlc": 2}
        subscriber.set_filter(filter_criteria)
        assert subscriber.filter == filter_criteria

    def test_multiple_subscribers(self):
        """Test multiple subscribers receiving same frame."""
        callback1_count = 0
        callback2_count = 0

        def callback1(frame):
            nonlocal callback1_count
            callback1_count += 1

        def callback2(frame):
            nonlocal callback2_count
            callback2_count += 1

        subscriber1 = CANSubscriber("sub1", callback=callback1)
        subscriber2 = CANSubscriber("sub2", callback=callback2)

        bus = CANBus()
        bus.add_subscriber(subscriber1)
        bus.add_subscriber(subscriber2)

        frame = CANFrame(id=0x100, data=b"\x01", dlc=1)
        bus.publish(frame)

        import time
        time.sleep(0.1)

        assert callback1_count == 1
        assert callback2_count == 1