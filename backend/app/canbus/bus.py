# Software CAN Bus Core

from __future__ import annotations
from typing import List, Optional, Callable, Set
from datetime import datetime
from threading import Lock
from .frame import CANFrame
from .filter import CANMessageFilter, CANMessageFilterBuilder
from .errors import (
    CANError,
    CANInvalidIdentifierError,
    CANInvalidDLCError,
    CANInvalidPayloadError,
    CANSubscriberError,
)


class CANBus:
    """
    Central CAN bus implementation that manages message flow between
    publishers and subscribers in a virtual automotive environment.
    """

    def __init__(self, bus_name: str = "virtual_can") -> None:
        self.bus_name = bus_name
        self._subscribers: Set[CANSubscriber] = set()
        self._message_history: List[CANFrame] = []
        self._history_size = 1000  # Keep 1000 frames in history
        self._lock = Lock()  # Thread safety for concurrent access
        self._bus_error = None

    def add_subscriber(self, subscriber: CANSubscriber) -> None:
        """Add a subscriber to the bus."""
        with self._lock:
            self._subscribers.add(subscriber)

    def remove_subscriber(self, subscriber_id: str) -> None:
        """Remove a subscriber by ID."""
        with self._lock:
            self._subscribers = {s for s in self._subscribers if s.subscriber_id != subscriber_id}

    def publish(self, frame: CANFrame) -> bool:
        """
        Publish a CAN frame to the bus.

        Args:
            frame: The CAN frame to publish

        Returns:
            True if published successfully, False if invalid
        """
        # Validate the frame
        if not self._validate_frame(frame):
            return False

        # Add to message history
        with self._lock:
            self._message_history.append(frame)
            if len(self._message_history) > self._history_size:
                self._message_history = self._message_history[-self._history_size:]
            # Snapshot subscribers INSIDE the lock, then dispatch OUTSIDE to avoid
            # re-entrant deadlock (a callback may call publish() again).
            subscribers_snapshot = list(self._subscribers)

        # Dispatch outside the lock — safe because we work on the snapshot
        for subscriber in subscribers_snapshot:
            try:
                subscriber.receive(frame)
            except Exception:
                pass

        return True

    def get_message_history(self, filter_criteria: Optional = None) -> List[CANFrame]:
        """
        Get message history with optional filtering.

        Args:
            filter_criteria: Optional filter to apply to the history

        Returns:
            List of CANFrame objects matching the filter
        """
        with self._lock:
            frames = list(self._message_history)

        if filter_criteria is not None:
            from .filter import CANMessageFilter
            if isinstance(filter_criteria, CANMessageFilter):
                frames = filter_criteria.filter_frames(frames)
            elif isinstance(filter_criteria, dict):
                # Simple dict-based filtering
                filtered_frames = []
                for frame in frames:
                    matches = True
                    for key, value in filter_criteria.items():
                        if key == "can_id" and frame.id != value:
                            matches = False
                            break
                        if key == "dlc" and frame.dlc != value:
                            matches = False
                            break
                        if key == "data_prefix" and not frame.data.startswith(value):
                            matches = False
                            break
                        if key == "is_rtr" and frame.is_rtr != value:
                            matches = False
                            break
                        if key == "is_extended" and frame.is_extended != value:
                            matches = False
                            break
                        if key == "timestamp_min" and frame.timestamp < value:
                            matches = False
                            break
                        if key == "timestamp_max" and frame.timestamp > value:
                            matches = False
                            break
                    if matches:
                        filtered_frames.append(frame)
                frames = filtered_frames

        return frames

    def get_subscribers(self) -> Set[CANSubscriber]:
        """Get current subscribers."""
        with self._lock:
            return self._subscribers.copy()

    def get_message_count(self) -> int:
        """Get total number of messages published."""
        with self._lock:
            return len(self._message_history)

    def clear_history(self) -> None:
        """Clear message history."""
        with self._lock:
            self._message_history = []

    def set_bus_error(self, error: CANError) -> None:
        """Set an error for the bus."""
        with self._lock:
            self._bus_error = error

    def get_bus_error(self) -> Optional[CANError]:
        """Get current bus error."""
        with self._lock:
            return self._bus_error

    def _validate_frame(self, frame: CANFrame) -> bool:
        """Validate a CAN frame for consistency with bus rules."""
        try:
            # Validate CAN ID (11-bit standard)
            if not (0 <= frame.id <= 0x7FF):
                raise CANInvalidIdentifierError(f"CAN ID {frame.id} out of 11-bit range")

            # Validate DLC
            if not (0 <= frame.dlc <= 8):
                raise CANInvalidDLCError(f"DLC {frame.dlc} out of range [0, 8]")

            # Validate payload length
            if len(frame.data) != frame.dlc:
                raise CANInvalidPayloadError(
                    f"Data length {len(frame.data)} doesn't match DLC {frame.dlc}"
                )

            # Validate data content
            if len(frame.data) > 8:
                return False  # Not a standard frame

            return True
        except CANError:
            # Re-raise CAN errors
            raise
        except Exception as e:
            # Handle unexpected errors
            self.set_bus_error(CANError(f"Frame validation failed: {str(e)}"))
            return False

    def get_stats(self) -> dict:
        """Get bus statistics."""
        with self._lock:
            return {
                "total_messages": len(self._message_history),
                "subscriber_count": len(self._subscribers),
                "history_size": self._history_size,
                "bus_error": self._bus_error,
            }