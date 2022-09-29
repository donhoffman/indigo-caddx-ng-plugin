#! /usr/bin/env python
# -*- coding: utf-8 -*-

import queue

# noinspection PyUnresolvedReferences
import indigo

import constants as const


class Plugin(indigo.PluginBase):

    def __init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs):
        indigo.PluginBase.__init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs)
        self.debug = plugin_prefs.get("debugMode", False)
        if self.debug:
            indigo.server.log("Debug logging enabled")
        else:
            indigo.server.log("Debug logging disabled")
        self._conn = None
        self._plugin_id = plugin_id
        self._plugin_display_name = plugin_display_name
        self._queue = None
        self._sleep_between_polls = 0.05

    def startup(self):
        self.logger.debug("startup called")

    def shutdown(self):
        self.logger.debug("shutdown called")

    def deviceStartComm(self, device):
        self.logger.debug(f"{device.name}: Starting {device.deviceTypeId} device '{device.id}'")

    def deviceStopComm(self, device):
        self.logger.debug(f"{device.name}: Stopping {device.deviceTypeId} device '{device.id}'")

    def runConcurrentThread(self):
        # Set up to run loop
        self.logger.debug("runConcurrentThread called")
        if not self.pluginPrefs.get(const.PluginPrefsKeys.port, None):
            self.logger.error(f"{self._plugin_display_name}: No serial port configured.")
            return
        serialUrl = self.getSerialPortUrl(self.pluginPrefs[const.PluginPrefsKeys.port])
        self._conn = self.openSerial(self._plugin_display_name, serialUrl, self.pluginPrefs[const.PluginPrefsKeys.baud], writeTimeout=1.0)
        if not self._conn:
            self.logger.error(f"{self._plugin_display_name}: Unable to open serial port at {serialUrl}.")
            return
        self.logger.debug(f"Serial connection opened on '{serialUrl}'")
        self._conn.reset_input_buffer()
        self._queue = queue.Queue()

        # Send Interface Configuration Request to get panel operational parameters.  Results processed in _process_message()
        self._send_interface_configuration_request()

        try:
            self.logger.info(f"{self._plugin_display_name}: Communication loop started")
            while not self.stopThread:
                self.sleep(self._sleep_between_polls)

                # Check for broadcast messages
                received_message = self._read_message(wait_for_response=False)
                if received_message:
                    self.logger.debug(f"Received message: {received_message}")
                    self._process_received_message(received_message)

                # Process the command queue
                self._process_command_queue()

        except self.StopThread:
            self.logger.info(f"{self._plugin_display_name}: Communication loop stopped")
        finally:
            self._conn.close()
            while not self._queue.empty():
                # noinspection PyUnusedLocal
                item = self._queue.get_nowait()
                self._queue.task_done()
            self._queue = None
            self.logger.debug(f"Serial connection closed on '{self.pluginPrefs[const.PluginPrefsKeys.port]}'")

    def validatePrefsConfigUi(self, values_dict):
        errors_dict = indigo.Dict()
        self.validateSerialPortUI(values_dict, errors_dict, "serialPort")
        if "serialBaudRate" not in values_dict:
            errors_dict["serialBaudRate"] = "Missing baud rate. Reconfigure and reload the Caddx plugin."
        if "debugMode" not in values_dict:
            errors_dict[u'debugMode'] = "Missing debug parameter. Reconfigure and reload the Caddx plugin."
        if errors_dict:
            return False, values_dict, errors_dict
        return True, values_dict

    def _read_message(self, wait_for_response=True) -> None | bytearray:
        """
        Read complete message from the serial port.
        :param wait_for_response: If True, wait for a response message from the serial port.
            If False, return immediately if no message.
        :return: None if no message received, otherwise the message received.
        """
        if not wait_for_response and not self._conn.in_waiting():
            return None

        start_character = self._conn.read(1)
        if start_character != b'\x7e':
            self.logger.error("Invalid or missing start character. Flushing and discarding buffer.")
            self._conn.reset_input_buffer()
            return None
        message_length_byte = self._conn.read(1)
        if not message_length_byte:
            self.logger.error("Invalid or missing message length. Flushing and discarding buffer.")
            self._conn.reset_input_buffer()
            return None
        message_data = bytearray()
        message_data.extend(message_length_byte)
        message_length = int.from_bytes(message_length_byte, byteorder='little')
        for i in range(message_length + 2):  # +2 for checksum
            next_char = self._conn.read(1)
            if next_char == b'\x7d':
                next_char = self._conn.read(1)
                if next_char == b'\x5e':
                    next_char = b'\x7e'
                elif next_char == b'\x5d':
                    next_char = b'\x7d'
                else:
                    self.logger.error("Invalid escape sequence. Flushing and discarding buffer.")
                    self._conn.reset_input_buffer()
                    return None
            message_data.extend(next_char)
        if len(message_data) != message_length + 3:  # +3 for length and checksum. Both will be stripped off later.
            self.logger.error("Message data wrong length. Flushing and discarding buffer.")
            self._conn.reset_input_buffer()
            return None

        # Check the checksum
        offered_checksum = int.from_bytes(message_data[-2:], byteorder='little')
        del message_data[-2:]  # Strip off the checksum
        calculated_checksum = self._calculate_fletcher16(message_data)
        if offered_checksum != calculated_checksum:
            self.logger.error("Invalid checksum. Discarding message.")
            return None

        # Strip off the length byte
        del message_data[0]
        return message_data

    def _calculate_fletcher16(self, data: bytearray) -> int:
        """
        Calculate the Fletcher-16 checksum for the given data.
        :param data: The data to be checksummed.
        :return: 16-bit checksum.
        """
        sum1 = int(0)
        sum2 = int(0)
        for byte in data:
            sum1 = (sum1 + byte) % 255
            sum2 = (sum2 + sum1) % 255
        return (sum2 << 8) | sum1

    def _process_received_message(self, message: bytearray) -> None:
        """
        Process received messages.

        :param message: The received message, starting from command byte.
        :return: None.
        """
        message_type = message[0]
        ack_requested = bool(message_type & 0x80)
        message_type &= ~0xc0
        if len(message) < const.MessageValidLength[message_type]:
            self.logger.error(f"Invalid message length for type. Discarding message.")
            return
        match message_type:
            case const.MessageType.IntConfigRsp:
                self._process_int_config_rsp(message)
            case _:  # Unknown message type
                self.logger.error(f"Unsupported message type: {message_type}")

        if ack_requested:  # OK to ACK even unsupported message types
            self._send_message_ack()

    def _process_int_config_rsp(self, message: bytearray) -> None:
        """
        Process IntConfigRsp message.

        :param message: The received message, starting from command byte.
        :return: None.
        """
        self.pluginPrefs[const.PluginPrefsKeys.panel_firmware] = message[1:6].decode('ascii')
        self.logger.debug(f"Panel firmware: {self.pluginPrefs[const.PluginPrefsKeys.panel_firmware]}")

        transition_message_flags1 = self.pluginPrefs[const.PluginPrefsKeys.transition_message_flags1] = message[5] & 0xff
        transition_message_flags2 = self.pluginPrefs[const.PluginPrefsKeys.transition_message_flags2] = message[6] & 0xff
        request_command_flags1 = self.pluginPrefs[const.PluginPrefsKeys.request_command_flags1] = message[7] & 0xff
        request_command_flags2 = self.pluginPrefs[const.PluginPrefsKeys.request_command_flags2] = message[8] & 0xff
        request_command_flags3 = self.pluginPrefs[const.PluginPrefsKeys.request_command_flags3] = message[9] & 0xff
        request_command_flags4 = self.pluginPrefs[const.PluginPrefsKeys.request_command_flags4] = message[10] & 0xff

        # Log enabled transition-based broadcast messages
        self.logger.debug("Transition-based broadcast messages enabled:")
        for message_type in const.TransitionMessageFlags1:
            self.logger.debug(f"  - {message_type.name}: {bool(transition_message_flags1 & message_type.value())}")
        for message_type in const.TransitionMessageFlags2:
            self.logger.debug(f"  - {message_type.name}: {bool(transition_message_flags2 & message_type.value())}")

        # Log enabled command/request messages
        self.logger.debug("Command/request messages enabled:")
        for message_type in const.RequestCommandFlags1:
            self.logger.debug(f"  - {message_type.name}: {bool(request_command_flags1 & message_type)}")
        for message_type in const.RequestCommandFlags2:
            self.logger.debug(f"  - {message_type.name}: {bool(request_command_flags2 & message_type)}")
        for message_type in const.RequestCommandFlags3:
            self.logger.debug(f"  - {message_type.name}: {bool(request_command_flags3 & message_type)}")
        for message_type in const.RequestCommandFlags4:
            self.logger.debug(f"  - {message_type.name}: {bool(request_command_flags4 & message_type)}")

        # Check for that all required messages are enabled
        required_message_disabled = False
        if not transition_message_flags1 & const.TransitionMessageFlags1.InterfaceConfig:
            self.logger.error("Interface Config Message is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not transition_message_flags1 & const.TransitionMessageFlags1.ZoneStatus:
            self.logger.error("Zone Status Message is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not transition_message_flags1 & const.TransitionMessageFlags1.PartitionStatus:
            self.logger.error("Partition Status Message is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not transition_message_flags1 & const.TransitionMessageFlags1.PartitionSnapshot:
            self.logger.error("Partition Snapshot Message is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not transition_message_flags2 & const.TransitionMessageFlags2.SystemStatus:
            self.logger.error("System Status Message is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not request_command_flags1 & const.RequestCommandFlags1.InterfaceConfig:
            self.logger.error("Interface Config Request is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not request_command_flags1 & const.RequestCommandFlags1.ZoneName:
            self.logger.error("Zone Name Request is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not request_command_flags1 & const.RequestCommandFlags1.ZoneStatus:
            self.logger.error("Zone Status Request is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not request_command_flags1 & const.RequestCommandFlags1.ZoneSnapshot:
            self.logger.error("Zone Snapshot Request is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not request_command_flags1 & const.RequestCommandFlags1.PartitionStatus:
            self.logger.error("Partition Status Request is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not request_command_flags1 & const.RequestCommandFlags1.PartitionSnapshot:
            self.logger.error("Partition Snapshot Request is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not request_command_flags2 & const.RequestCommandFlags2.SystemStatus:
            self.logger.error("System Status Request is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not request_command_flags4 & const.RequestCommandFlags4.SetClockCalendar:
            self.logger.error("Set Clock/Calendar Request is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if not request_command_flags4 & const.RequestCommandFlags4.PrimaryKeypadNoPin:
            self.logger.error("Primary Keypad No Pin Request is not enabled. This is required for proper operation.")
            required_message_disabled = True
        if required_message_disabled:
            self.logger.error("Please enable the required messages in the Caddx panel configuration before starting plugin.")
            raise Exception("Required  messages not enabled in panel config")

    def _send_message(self, message_type: const.MessageType, message_data: bytearray = None) -> None:
        """
        Send a message to the panel.

        :param message_type: The message type to send.
        :param message_data: Ancillary message data, if used.

        :return: None
        """
        message_length = 1 + len(message_data) if message_data else 1
        if not message_type not in const.MessageValidLength:
            self.logger.error(f"Unsupported message type: {message_type}")
            return
        if not message_length == const.MessageValidLength[message_type]:
            self.logger.error(f"Invalid message length for message type {message_type.name}. Expected {const.MessageValidLength[message_type]}, got {message_length}")
            return

        # Build the message
        message = bytearray()
        message.append(message_length & 0xff)
        message.append(message_type.value())
        if message_data:
            message.extend(message_data)
        checksum = self._calculate_fletcher16(message)
        message.extend(checksum.to_bytes(2, byteorder="little"))

        # Byte-stuff the message
        message_stuffed = bytearray()
        for i in message:
            if i == 0x7e:
                message_stuffed.append(0x7d)
                message_stuffed.append(0x5e)
            elif i == 0x7d:
                message_stuffed.append(0x7d)
                message_stuffed.append(0x5d)
            else:
                message_stuffed.append(i)
        message_stuffed[0:0] = 0x7e
        self._conn.write(message_stuffed)
        self.logger.debug(f"Sent message: {message_stuffed.hex()}")

    def _send_message_ack(self) -> None:
        """
        Send an acknowledgement message.

        :return: None.
        """
        self.logger.debug("Sending acknowledgement message")
        self._send_message(const.MessageType.ACK, message_data=None)

    def _send_message_nak(self) -> None:
        """
        Send a negative acknowledgement message.

        :return: None.
        """
        self.logger.debug("Sending negative acknowledgement message")
        self._send_message(const.MessageType.NACK, message_data=None)

    def _send_interface_configuration_request(self) -> None:
        """
        Send an Interface Configuration Request message.

        :return: None.
        """
        self.logger.debug("Sending Interface Configuration Request message")
        self._send_message(const.MessageType.IntConfigReq, message_data=None)
