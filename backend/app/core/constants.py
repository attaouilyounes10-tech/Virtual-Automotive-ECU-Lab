# CAN Protocol Constants
CAN_MAX_ID = 0x7FF  # 11-bit standard identifiers
CAN_MAX_DLC = 8       # Max data length (bytes)
CAN_MIN_DLC = 0       # Min data length (bytes)

# Message Types (ECU identifiers)
CAN_ID_ADAS_STATUS = 0x100
CAN_ID_COLLISION_WARNING = 0x101
CAN_ID_VEHICLE_STATUS = 0x200
CAN_ID_BRAKE_COMMAND = 0x201
CAN_ID_DASHBOARD_ALERT = 0x300
CAN_ID_SYSTEM_DIAGNOSTICS = 0x700

# CAN Frame Structure
CAN_FRAME_ID_SIZE = 11  # 11-bit identifier
CAN_FRAME_DLC_SIZE = 1  # Data Length Code size
CAN_FRAME_DATA_SIZE = 8 # Max data bytes

# CAN Bus Configuration
CAN_BUS_NAME = "virtual_can"
CAN_BUS_BITRATE = 500000  # 500 kbps typical automotive bus
CAN_BUS_ERROR_HANDLING = True