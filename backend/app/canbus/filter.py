# CAN Message Filter

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
from .frame import CANFrame
from .errors import CANFilterError


@dataclass
class CANMessageFilter:
    """
    Filter for CAN messages based on various criteria.

    Supports filtering by:
    - CAN ID (exact match or range)
    - DLC value
    - Data pattern (prefix match)
    - RTR frame type
    - Extended frame format
    - Time range
    """

    # ID filtering
    can_id: Optional[int] = None
    can_id_min: Optional[int] = None
    can_id_max: Optional[int] = None

    # DLC filtering
    dlc: Optional[int] = None
    dlc_min: Optional[int] = None
    dlc_max: Optional[int] = None

    # Data pattern filtering (matches prefix)
    data_prefix: Optional[bytes] = None

    # Frame type filtering
    is_rtr: Optional[bool] = None
    is_extended: Optional[bool] = None

    # Time filtering
    timestamp_min: Optional[float] = None
    timestamp_max: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate filter parameters."""
        if self.can_id_min is not None and self.can_id_max is not None:
            if self.can_id_min > self.can_id_max:
                raise CANFilterError("can_id_min cannot be greater than can_id_max")

        if self.dlc_min is not None and self.dlc_max is not None:
            if self.dlc_min > self.dlc_max:
                raise CANFilterError("dlc_min cannot be greater than dlc_max")

        if self.timestamp_min is not None and self.timestamp_max is not None:
            if self.timestamp_min > self.timestamp_max:
                raise CANFilterError("timestamp_min cannot be greater than timestamp_max")

    def matches(self, frame: CANFrame) -> bool:
        """Check if a frame matches all filter criteria."""
        # CAN ID exact match
        if self.can_id is not None and frame.id != self.can_id:
            return False

        # CAN ID range
        if self.can_id_min is not None and frame.id < self.can_id_min:
            return False
        if self.can_id_max is not None and frame.id > self.can_id_max:
            return False

        # DLC exact match
        if self.dlc is not None and frame.dlc != self.dlc:
            return False

        # DLC range
        if self.dlc_min is not None and frame.dlc < self.dlc_min:
            return False
        if self.dlc_max is not None and frame.dlc > self.dlc_max:
            return False

        # Data prefix match
        if self.data_prefix is not None:
            if not frame.data.startswith(self.data_prefix):
                return False

        # RTR filter
        if self.is_rtr is not None and frame.is_rtr != self.is_rtr:
            return False

        # Extended filter
        if self.is_extended is not None and frame.is_extended != self.is_extended:
            return False

        # Time range
        if self.timestamp_min is not None and frame.timestamp < self.timestamp_min:
            return False
        if self.timestamp_max is not None and frame.timestamp > self.timestamp_max:
            return False

        return True

    def filter_frames(self, frames: List[CANFrame]) -> List[CANFrame]:
        """Filter a list of frames."""
        return [frame for frame in frames if self.matches(frame)]


class CANMessageFilterBuilder:
    """Builder pattern for creating complex filters."""

    def __init__(self) -> None:
        self._filter = CANMessageFilter()

    def with_can_id(self, can_id: int) -> CANMessageFilterBuilder:
        self._filter.can_id = can_id
        return self

    def with_can_id_range(self, min_id: int, max_id: int) -> CANMessageFilterBuilder:
        self._filter.can_id_min = min_id
        self._filter.can_id_max = max_id
        return self

    def with_dlc(self, dlc: int) -> CANMessageFilterBuilder:
        self._filter.dlc = dlc
        return self

    def with_dlc_range(self, min_dlc: int, max_dlc: int) -> CANMessageFilterBuilder:
        self._filter.dlc_min = min_dlc
        self._filter.dlc_max = max_dlc
        return self

    def with_data_prefix(self, prefix: bytes) -> CANMessageFilterBuilder:
        self._filter.data_prefix = prefix
        return self

    def with_rtr(self, is_rtr: bool) -> CANMessageFilterBuilder:
        self._filter.is_rtr = is_rtr
        return self

    def with_extended(self, is_extended: bool) -> CANMessageFilterBuilder:
        self._filter.is_extended = is_extended
        return self

    def with_time_range(self, min_ts: float, max_ts: float) -> CANMessageFilterBuilder:
        self._filter.timestamp_min = min_ts
        self._filter.timestamp_max = max_ts
        return self

    def build(self) -> CANMessageFilter:
        return self._filter