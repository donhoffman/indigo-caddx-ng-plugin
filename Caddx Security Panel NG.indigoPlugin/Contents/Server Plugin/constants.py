from enum import IntEnum
from typing import NamedTuple, Set
from types import MappingProxyType


class PluginPrefsKeys(NamedTuple):
    """Plugin configuration keys."""
    port: str = "serialPort"
    baud: str = "serialBaudRate"
    debug: str = "debugMode"
    panel_firmware: str = "panelFirmware"
    transition_message_flags1: str = "transitionMessageFlags1"
    transition_message_flags2: str = "transitionMessageFlags2"
    request_command_flags1: str = "requestCommandFlags1"
    request_command_flags2: str = "requestCommandFlags2"
    request_command_flags3: str = "requestCommandFlags3"
    request_command_flags4: str = "requestCommandFlags4"

# General constants that apply to all message types


class MessageType(IntEnum):
    IntConfigRsp = 0x01,            # Interface Configuration (Response)
    ZoneNameRsp = 0x03,             # Zone Name (Response)
    ZoneStatusRsp = 0x04,           # Zone Status (Response)
    ZonesSnapshotRsp = 0x05,        # Zones Snapshot (Response)
    PartitionStatusRsp = 0x06,      # Partition Status (Response)
    PartitionSnapshotRsp = 0x07,    # Partition Snapshot (Response)
    SystemStatusRsp = 0x08,         # System Status (Response)
    X10MessageInd = 0x09,           # X10 Message (Indication)
    LogEventInd = 0x0A,             # Log Event (Indication)
    KeypadButtonInd = 0x0B,         # Keypad Button (Response)
    ProgramDataRsp = 0x10,          # Program Data Reply (Response)
    UserInfoRsp = 0x12,             # User Info Reply (Response)
    FailedRequest = 0x1c,           # Failed Request (Response)
    ACK = 0x1d,                     # Acknowledge (Response)
    NACK = 0x1e,                    # Negative Acknowledge (Response)
    Rejected = 0x1f,                # Rejected (Response)

    IntConfigReq = 0x21,            # Interface Configuration (Request)
    ZoneNameReq = 0x23,             # Zone Name (Request)
    ZoneStatusReq = 0x24,           # Zone Status (Request)
    ZonesSnapshotReq = 0x25,        # Zones Snapshot (Request)
    PartitionStatusReq = 0x26,      # Partition Status (Request)
    PartitionSnapshotReq = 0x27,    # Partition Snapshot (Request)
    SystemStatusReq = 0x28,         # System Status (Request)
    X10MessageReq = 0x29,           # X10 Message (Request)
    LogEventReq = 0x2A,             # Log Event (Request)
    KeypadTextMsgReq = 0x2B,        # Keypad Text Message (Request)
    KeypadTerminalModeReq = 0x2C,   # Keypad Terminal Mode (Request)
    ProgramDataReq = 0x30,          # Program Data Request (Request)
    ProgramDataCmd = 0x31,          # Program Data Command (Request)
    UserInfoReqPin = 0x32,          # User Info Request with PIN (Request)
    UserInfoReqNoPin = 0x33,        # User Info Request without PIN (Request)
    SetUserCodePin = 0x34,          # Set User Code with PIN (Request)
    SetUserCodeNoPin = 0x35,        # Set User Code without PIN (Request)
    SetUserAuthorityPin = 0x36,     # Set User Authority with PIN (Request)
    SetUserAuthorityNoPin = 0x37,   # Set User Authority without PIN (Request)
    SetClockCalendar = 0x3B,        # Set Clock/Calendar (Request)
    PrimaryKeypadFuncPin = 0x3C,    # Primary Keypad Function with PIN (Request)
    PrimaryKeypadFuncNoPin = 0x3D,  # Primary Keypad Function without PIN (Request)
    SecondaryKeypadFunc = 0x3E,     # Secondary Keypad Function (Request)
    ZoneBypassToggle = 0x3F,        # Zone Bypass Toggle (Request)


MessageValidLength = MappingProxyType(
    {
        MessageType.IntConfigRsp: 11,
        MessageType.ZoneNameRsp: 18,
        MessageType.ZoneStatusRsp: 8,
        MessageType.ZonesSnapshotRsp: 10,
        MessageType.PartitionStatusRsp: 9,
        MessageType.PartitionSnapshotRsp: 9,
        MessageType.SystemStatusRsp: 12,
        MessageType.X10MessageInd: 4,
        MessageType.LogEventInd: 10,
        MessageType.KeypadButtonInd: 3,
        MessageType.ProgramDataRsp: 13,
        MessageType.UserInfoRsp: 17,
        MessageType.FailedRequest: 1,
        MessageType.ACK: 1,
        MessageType.NACK: 1,
        MessageType.Rejected: 1,

        MessageType.IntConfigReq: 1,
        MessageType.ZoneNameReq: 2,
        MessageType.ZoneStatusReq: 2,
        MessageType.ZonesSnapshotReq: 2,
        MessageType.PartitionStatusReq: 2,
        MessageType.PartitionSnapshotReq: 1,
        MessageType.SystemStatusReq: 1,
        MessageType.X10MessageReq: 4,
        MessageType.LogEventReq: 2,
        MessageType.KeypadTextMsgReq: 12,
        MessageType.KeypadTerminalModeReq: 3,
        MessageType.ProgramDataReq: 4,
        MessageType.ProgramDataCmd: 13,
        MessageType.UserInfoReqPin: 5,
        MessageType.UserInfoReqNoPin: 2,
        MessageType.SetUserCodePin: 8,
        MessageType.SetUserCodeNoPin: 5,
        MessageType.SetUserAuthorityPin: 7,
        MessageType.SetUserAuthorityNoPin: 4,
        MessageType.SetClockCalendar: 7,
        MessageType.PrimaryKeypadFuncPin: 6,
        MessageType.PrimaryKeypadFuncNoPin: 4,
        MessageType.SecondaryKeypadFunc: 3,
        MessageType.ZoneBypassToggle: 2,
    }
)

CommandInfo = NamedTuple('CaddxCommand', [
    ('command', MessageType),
    ('length', int),
    ('valid_response', Set[MessageType]),
])


# Interface Configuration (Response) constants
class TransitionMessageFlags1(IntEnum):
    InterfaceConfig = 0b00000010,       # Interface Configuration response
    ZoneStatus = 0b00010000,            # Zone Status response
    ZoneSnapshot = 0b00100000,          # Zone Snapshot response
    PartitionStatus = 0b01000000,       # Partition Status response
    PartitionSnapshot = 0b10000000,     # Partition Snapshot response


class TransitionMessageFlags2(IntEnum):
    SystemStatus = 0b00000001,          # System Status response
    X10Message = 0b00000010,            # X10 Message indication
    LogEvent = 0b00000100,              # Log Event response/indication
    KeypadButton = 0b00001000,          # Keypad Button response


class RequestCommandFlags1(IntEnum):
    InterfaceConfig = 0b00000010,       # Interface Configuration request
    ZoneName = 0b00001000,              # Zone Name request
    ZoneStatus = 0b00010000,            # Zone Status request
    ZoneSnapshot = 0b00100000,          # Zone Snapshot request
    PartitionStatus = 0b01000000,       # Partition Status request
    PartitionSnapshot = 0b10000000,     # Partition Snapshot request


class RequestCommandFlags2(IntEnum):
    SystemStatus = 0b00000001,          # System Status request
    X10Message = 0b00000010,            # X10 Message request
    LogEvent = 0b00000100,              # Log Event request
    KeypadTextMessage = 0b00001000,     # Keypad Text Message request
    KeypadTerminalMode = 0b00010000,    # Keypad Terminal Mode request


class RequestCommandFlags3(IntEnum):
    ProgramData = 0b00000001,           # Program Data request
    ProgramDataCommand = 0b00000010,    # Program Data command
    UserInfoPin = 0b00000100,           # User Info request with PIN
    UserInfoNoPin = 0b00001000,         # User Info request without PIN
    SetUserCodePin = 0b00010000,        # Set User Code with PIN
    SetUserCodeNoPin = 0b00100000,      # Set User Code without PIN
    SetUserAuthorityPin = 0b01000000,   # Set User Authority with PIN
    SetUserAuthorityNoPin = 0b10000000,  # Set User Authority without PIN


class RequestCommandFlags4(IntEnum):
    SetClockCalendar = 0b00001000,      # Set Clock/Calendar
    PrimaryKeypadPin = 0b00010000,      # Primary Keypad Function with PIN
    PrimaryKeypadNoPin = 0b00100000,    # Primary Keypad Function without PIN
    SecondaryKeypad = 0b01000000,       # Secondary Keypad Function
    ZoneBypassToggle = 0b10000000,      # Zone Bypass Toggle
