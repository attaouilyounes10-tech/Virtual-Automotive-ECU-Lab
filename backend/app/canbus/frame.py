# CAN Frame Model

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from ..core.constants import (
    CAN_MAX_ID,
    CAN_MAX_DLC,
    CAN_MIN_DLC,
)
from .errors import (
    CANInvalidIdentifierError,
    CANInvalidDLCError,
    CANInvalidPayloadError,
)


@dataclass
class CANFrame:
    """Represents a single CAN frame (2.0A standard 11-bit)."""

    id: int
    data: bytes
    dlc: int  # Data Length Code (0-8)
    is_rtr: bool = False  # Remote Transmission Request
    is_extended: bool = False  # Extended frame format (2.0B)
    timestamp: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate the CAN frame after initialization."""
        # Validate identifier (11-bit standard)
        if not (0 <= self.id <= CAN_MAX_ID):
            raise CANInvalidIdentifierError(
                f"CAN ID {self.id} is out of range [0, {CAN_MAX_ID}]"
            )

        # Validate DLC (0-8)
        if not (CAN_MIN_DLC <= self.dlc <= CAN_MAX_DLC):
            raise CANInvalidDLCError(
                f"DLC {self.dlc} is out of range [{CAN_MIN_DLC}, {CAN_MAX_DLC}]"
            )

        # Validate data length matches DLC
        if len(self.data) > self.dlc:
            raise CANInvalidPayloadError(
                f"Data length {len(self.data)} exceeds DLC {self.dlc}"
            )

        # Pad data to DLC length if shorter (standard CAN behavior)
        if len(self.data) < self.dlc:
            self.data = self.data + bytes(self.dlc - len(self.data))

        # Timestamps default to now
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()

    @property
    def is_standard(self) -> bool:
        """Check if this is a standard 11-bit frame."""
        return not self.is_extended

    @property
    def payload_hex(self) -> str:
        """Return data as hex string for display."""
        return self.data.hex()

    @property
    def can_id_hex(self) -> str:
        """Return CAN ID as zero-padded hex string."""
        return f"0x{self.id:03X}"

    def encode(self) -> bytes:
        """Encode the frame to raw CAN bytes."""
        # Standard 11-bit frame format:
        # 11-bit ID + RTR bit + 0 + DLC (3 bits) + data
        # For simplicity, we return a structured representation
        return {
            "id": self.id,
            "dlc": self.dlc,
            "data": self.data.hex(),
            "is_rtr": self.is_rtr,
            "is_extended": self.is_extended,
        }

    @classmethod
    def decode(cls, raw: dict) -> CANFrame:
        """Decode from a dictionary (e.g., from encode or external source)."""
        return cls(
            id=raw.get("id", 0),
            data=bytes.fromhex(raw.get("data", "00" * CAN_MAX_DLC)),
            dlc=raw.get("dlc", CAN_MIN_DLC),
            is_rtr=raw.get("is_rtr", False),
            is_extended=raw.get("is_extended", False),
            timestamp=raw.get("timestamp"),
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        rtr_str = "RTR" if self.is_rtr else ""
        extended_str = "EXT" if self.is_extended else ""
        return (
            f"CAN {self.can_id_hex} [{self.dlc}] {self.payload_hex} "
            f"{rtr_str} {extended_str} @{self.timestamp:.3f}"
        )

    def __repr__(self) -> str:
        return f"CANFrame(id={self.id}, dlc={self.dlc}, data={self.payload_hex!r})"