# CAN Database Loader with cantools

from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any
import cantools
from ..core.constants import (
    CAN_MAX_ID,
    CAN_MAX_DLC,
    CAN_MIN_DLC,
)
from .errors import (
    CANError,
    CANInvalidIdentifierError,
    CANInvalidDLCError,
    CANInvalidPayloadError,
)


class CANDbcLoader:
    """
    Loads a CAN database (DBC file) using cantools and provides
    encoding/decoding services for CAN frames.

    This module bridges the Phase 1 CAN bus implementation
    with cantools DBC-based signal encoding/decoding.
    """

    def __init__(self, dbc_path: Optional[str] = None) -> None:
        """
        Initialize the DBC loader.

        Args:
            dbc_path: Path to the DBC file. If None, defaults to
                      backend/dbc/vael_can.dbc relative to this file.
        """
        self.dbc_path: Optional[str] = dbc_path
        self._db: Optional[cantools.database.can.Database] = None
        self._loaded = False

    def load(self, dbc_path: Optional[str] = None) -> None:
        """
        Load the DBC file using cantools.

        Args:
            dbc_path: Path to the DBC file. Overrides the path set at init.

        Raises:
            CANError: If the DBC file cannot be loaded.
        """
        path = dbc_path or self.dbc_path or self._default_dbc_path()

        try:
            self._db = cantools.database.load_file(path)
            self.dbc_path = path
            self._loaded = True
        except FileNotFoundError as e:
            raise CANError(f"DBC file not found: {path}") from e
        except Exception as e:
            raise CANError(f"Failed to load DBC file '{path}': {str(e)}") from e

    def _default_dbc_path(self) -> str:
        """Resolve the default DBC path relative to this module."""
        here = Path(__file__).resolve()
        candidates = [
            here.parent.parent.parent / "dbc" / "vael_can.dbc",
            Path.cwd() / "backend" / "dbc" / "vael_can.dbc",
            Path.cwd() / "dbc" / "vael_can.dbc",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return str(candidates[0])

    @property
    def is_loaded(self) -> bool:
        """Check if the DBC database has been loaded."""
        return self._loaded and self._db is not None

    @property
    def messages(self) -> list:
        """Return all decoded DBC messages."""
        if not self.is_loaded:
            return []
        return list(self._db.messages)

    @property
    def can_messages(self) -> dict:
        """Return all DBC messages indexed by CAN ID."""
        if not self.is_loaded:
            return {}
        result = {}
        for msg in self.messages:
            result[msg.frame_id] = msg
        return result

    def get_message_by_id(self, can_id: int):
        """
        Get a DBC message definition by its CAN ID.

        Args:
            can_id: 11-bit CAN identifier.

        Returns:
            The message definition object, or None if not found.
        """
        if not self.is_loaded:
            return None
        try:
            return self._db.get_message_by_frame_id(can_id)
        except KeyError:
            return None

    def validate_id(self, can_id: int) -> None:
        """Validate that a CAN ID fits in 11 bits."""
        if not (0 <= can_id <= CAN_MAX_ID):
            raise CANInvalidIdentifierError(
                f"CAN ID {can_id} is out of 11-bit range [0, {CAN_MAX_ID}]"
            )

    def validate_dlc(self, dlc: int) -> None:
        """Validate DLC is within [0, 8]."""
        if not (CAN_MIN_DLC <= dlc <= CAN_MAX_DLC):
            raise CANInvalidDLCError(
                f"DLC {dlc} is out of range [{CAN_MIN_DLC}, {CAN_MAX_DLC}]"
            )

    def encode_message(self, can_id: int, signal_values: Dict[str, Any]) -> bytes:
        """
        Encode signal values into a CAN payload using the DBC definition.

        Args:
            can_id: 11-bit CAN identifier.
            signal_values: Dictionary mapping signal names to values.

        Returns:
            Encoded CAN payload bytes (DLC bytes).

        Raises:
            CANError: If the message ID is not in the DBC or encoding fails.
        """
        if not self.is_loaded:
            raise CANError("DBC database not loaded")

        self.validate_id(can_id)

        message = self.get_message_by_id(can_id)
        if message is None:
            raise CANError(
                f"CAN ID {can_id} (0x{can_id:03X}) not found in DBC database"
            )

        try:
            # Cantools requires all signals to be specified for encoding
            # Get the message's signal list
            if can_id == 0x201:  # BRAKE_COMMAND
                # BRAKE_COMMAND has Brake_Request, Brake_Force_N, Brake_Duration_ms
                # Additional signals like Emergency_Brake and Brake_Source are not in DBC
                # Use only required signals
                required_signals = [sig.name for sig in self._db.get_message_by_frame_id(can_id).signals]
                filtered_values = {k: v for k, v in signal_values.items() if k in required_signals}
                encoded = message.encode(filtered_values)
            else:
                encoded = message.encode(signal_values)
        except Exception as e:
            raise CANError(
                f"Failed to encode CAN ID {can_id}: {str(e)}"
            ) from e

        dlc = len(encoded)
        self.validate_dlc(dlc)

        return encoded

    def decode_message(
        self, can_id: int, data: bytes
    ) -> Dict[str, Any]:
        """
        Decode a CAN payload into signal values using the DBC definition.

        Args:
            can_id: 11-bit CAN identifier.
            data: Raw CAN data bytes.

        Returns:
            Dictionary mapping signal names to decoded values.

        Raises:
            CANError: If the message ID is not in the DBC or decoding fails.
        """
        if not self.is_loaded:
            raise CANError("DBC database not loaded")

        self.validate_id(can_id)

        message = self.get_message_by_id(can_id)
        if message is None:
            raise CANError(
                f"CAN ID {can_id} (0x{can_id:03X}) not found in DBC database"
            )

        try:
            decoded = message.decode(data)
        except Exception as e:
            raise CANError(
                f"Failed to decode CAN ID {can_id}: {str(e)}"
            ) from e

        # Return raw integer values, normalized later
        result: Dict[str, Any] = {}
        for name, val in decoded.items():
            result[name] = val
        return result

    def encode_can_frame(self, can_id: int, signal_values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encode a full CAN frame (ID + payload) using DBC definitions.

        Args:
            can_id: 11-bit CAN identifier.
            signal_values: Dictionary mapping signal names to values.

        Returns:
            Dictionary with id, dlc, data, data_hex, signal_values.

        Raises:
            CANError: If encoding fails.
        """
        data = self.encode_message(can_id, signal_values)
        return {
            "id": can_id,
            "dlc": len(data),
            "data": data,
            "data_hex": data.hex(),
            "signal_values": signal_values,
        }

    def decode_can_frame(self, can_id: int, data: bytes) -> Dict[str, Any]:
        """
        Decode a full CAN frame using DBC definitions.

        Args:
            can_id: 11-bit CAN identifier.
            data: Raw CAN data bytes.

        Returns:
            Dictionary with id, dlc, signals, data_hex.

        Raises:
            CANError: If decoding fails.
        """
        signals = self.decode_message(can_id, data)
        return {
            "id": can_id,
            "dlc": len(data),
            "signals": signals,
            "data_hex": data.hex(),
        }

    def get_signal_info(self, can_id: int) -> list[dict[str, Any]]:
        """
        Get signal definitions for a given message ID.

        Args:
            can_id: 11-bit CAN identifier.

        Returns:
            List of signal info dictionaries (name, start_bit, length,
            scale, offset, min, max, unit, is_signed).
        """
        if not self.is_loaded:
            return []

        message = self.get_message_by_id(can_id)
        if message is None:
            return []

        signals_info: list[dict[str, Any]] = []
        for sig in message.signals:
            signals_info.append({
                "name": sig.name,
                "start_bit": sig.start,
                "length": sig.length,
                "scale": sig.scale,
                "offset": sig.offset,
                "min": sig.minimum,
                "max": sig.maximum,
                "unit": sig.unit,
                "is_signed": sig.is_signed,
            })
        return signals_info

    def list_all_messages(self) -> list[dict[str, Any]]:
        """
        List all messages in the DBC database.

        Returns:
            List of message info dictionaries (frame_id, name, length/dlc,
            signals, cycle_time).
        """
        if not self.is_loaded:
            return []

        messages_info: list[dict[str, Any]] = []
        for msg in self.messages:
            signals_info: list[dict[str, Any]] = []
            for sig in msg.signals:
                signals_info.append({
                    "name": sig.name,
                    "start_bit": sig.start,
                    "length": sig.length,
                    "scale": sig.scale,
                    "offset": sig.offset,
                    "min": sig.minimum,
                    "max": sig.maximum,
                    "unit": sig.unit,
                    "is_signed": sig.is_signed,
                })

            sender_info = ""
            if msg.senders:
                sender_info = ", ".join(msg.senders)

            cycle_time = msg.cycle_time

            messages_info.append({
                "frame_id": msg.frame_id,
                "name": msg.name,
                "dlc": msg.length,
                "sender": sender_info,
                "signals": signals_info,
                "cycle_time": cycle_time,
            })
        return messages_info


dbc_loader = CANDbcLoader()