# CAN Bus Exceptions

class CANError(Exception):
    """Base exception for all CAN bus errors."""
    pass


class CANInvalidIdentifierError(CANError):
    """Raised when a CAN identifier is invalid."""
    pass


class CANInvalidDLCError(CANError):
    """Raised when a DLC is invalid."""
    pass


class CANInvalidPayloadError(CANError):
    """Raised when a payload length does not match DLC."""
    pass


class CANSubscriberError(CANError):
    """Raised for subscriber-related errors."""
    pass


class CANHistoryError(CANError):
    """Raised for message history errors."""
    pass


class CANFilterError(CANError):
    """Raised for message filtering errors."""
    pass


class CANBusError(CANError):
    """Raised for general bus errors."""
    pass