# CAN Bus Subscriber

from __future__ import annotations
from typing import Optional, List, Callable, Set
from datetime import datetime
from .frame import CANFrame
from .errors import CANSubscriberError


class CANSubscriber:
    """
    Represents a subscriber to the CAN bus.

    Subscribers receive CAN frames that match their criteria.
    A subscriber can have a callback function that is invoked
    when a matching frame is received.
    """

    def __init__(
        self,
        subscriber_id: str,
        callback: Optional[Callable[[CANFrame], None]] = None,
        filter_criteria: Optional = None,
    ) -> None:
        """
        Initialize a subscriber.

        Args:
            subscriber_id: Unique identifier for this subscriber
            callback: Optional callback function to invoke on frame receipt
            filter_criteria: Optional filter to apply to received frames
        """
        self.subscriber_id = subscriber_id
        self.callback = callback
        self.filter = filter_criteria
        self._message_count = 0
        self._last_message_time: Optional[float] = None
        self._frame_history: List[CANFrame] = []
        self._max_history = 100  # Keep last 100 frames by default

    def set_callback(self, callback: Callable[[CANFrame], None]) -> None:
        """Set or update the callback function."""
        self.callback = callback

    def set_filter(self, filter_criteria) -> None:
        """Set filter criteria for this subscriber."""
        self.filter = filter_criteria

    def receive(self, frame: CANFrame) -> None:
        """
        Receive a CAN frame if it matches the subscriber's filter.

        Args:
            frame: The CAN frame to receive
        """
        # Apply filter if defined
        if self.filter is not None:
            from .filter import CANMessageFilter
            if isinstance(self.filter, CANMessageFilter):
                if not self.filter.matches(frame):
                    return  # Frame doesn't match, discard silently
            elif isinstance(self.filter, dict):
                # Dict-based filter - simple matching
                if not self._matches_dict_filter(frame):
                    return

        # Update subscriber metrics
        self._message_count += 1
        self._last_message_time = datetime.now().timestamp()

        # Add to history (with size limit)
        self._frame_history.append(frame)
        if len(self._frame_history) > self._max_history:
            self._frame_history = self._frame_history[-self._max_history:]

        # Invoke callback if set
        if self.callback is not None:
            try:
                self.callback(frame)
            except Exception as e:
                # Log error but don't crash the bus
                pass

    def _matches_dict_filter(self, frame: CANFrame) -> bool:
        """Simple dict-based filter matching."""
        # This is a basic implementation; subclasses can override
        if "can_id" in self.filter and frame.id != self.filter["can_id"]:
            return False
        if "dlc" in self.filter and frame.dlc != self.filter["dlc"]:
            return False
        return True

    @property
    def message_count(self) -> int:
        """Total messages received."""
        return self._message_count

    @property
    def last_message_time(self) -> Optional[float]:
        """Timestamp of last received message."""
        return self._last_message_time

    @property
    def frame_history(self) -> List[CANFrame]:
        """Recent frame history."""
        return self._frame_history

    @property
    def is_active(self) -> bool:
        """Check if subscriber has received any messages."""
        return self._message_count > 0

    def clear_history(self) -> None:
        """Clear the frame history."""
        self._frame_history = []
        self._message_count = 0
        self._last_message_time = None