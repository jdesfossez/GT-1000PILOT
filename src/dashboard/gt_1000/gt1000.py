#!/usr/bin/env python3

import json
import rtmidi
import time
from time import sleep
from rtmidi.midiutil import open_midiinput, open_midioutput
from pathlib import Path

from .constants import (
    SYSEX_END,
    MODEL_ID,
    PATCH_NAMES_LEN,
    EDITOR_REPLY1,
    PATCH_NAMES_BEGIN_OFFSET,
    EDITOR_REPLY3,
    EDITOR_MODE_ADDRESS_FETCH1,
    EDITOR_MODE_ADDRESS_LEN1,
    EDITOR_MODE_ADDRESS_SET2,
    EDITOR_MODE_ADDESS_VALUE2,
    EDITOR_MODE_ADDRESS_FETCH3,
    EDITOR_MODE_ADDRESS_LEN3,
    DT1_SYSEX_HEADER,
    DT1_COMMAND_ID,
    RQ1_SYSEX_HEADER,
    SYSEX_START,
    IDENTITY_REQUEST_MSG,
    NON_RT_MSG,
    GEN_INFO,
    IDENTITY_REPLY,
    MANUFACTURER_ID,
    GT1000_FAMILY,
    DEVICE_ID_BCAST,
)

SLEEP_WAIT_SEC = 0.1
RETRY_COUNT = 100



def bytes_to_int(value):
    return int.from_bytes(value, byteorder="big")


def bytes_as_hex(data):
    return "[{}]".format(", ".join(hex(x) for x in data))


class MidiInputHandler(object):
    def __init__(self, port):
        self.port = port
        self._wallclock = time.time()

    def __call__(self, event, gt1000):
        message, deltatime = event
        self._wallclock += deltatime
        print(f"[%s] @%0.6f %s" % (self.port, self._wallclock, bytes_as_hex(message)))
        gt1000.process_received_message(message)


class GT1000:
    def __init__(self):
        self.tables = {}
        self.device_id = None
        self.current_state_message = None
        self.received_data = None
        for i in (Path(__file__).parent / "specs").glob("*.json"):
            table_name = i.name.split(".")[0]
            self.tables[table_name] = json.loads(i.read_text())

        # Aliases
        self.base_address_pointers = {
            "live_fx1": "patch (temporary patch)",
            "live_fx2": "patch (temporary patch)",
            "live_fx3": "patch (temporary patch)",
            "live_fx4": "patch3 (temporary patch)",
        }

    #        msg = self.build_dt_message(
    #            self.base_address_pointers["live_fx1"], "fx1", "FX1 TYPE", "DEFRETTER"
    #        )
    #        print_has_hex(msg)
    #        msg = self.build_dt_message(
    #            self.base_address_pointers["live_fx3"], "fx3", "FX1 TYPE", "FLANGER"
    #        )
    #        print_has_hex(msg)

    def request_identity(self):
        # TODO: this should be a background thread so we update the ID if the
        # device comes online at some point
        for i in range(RETRY_COUNT):
            self.send_message(IDENTITY_REQUEST_MSG)
            sleep(SLEEP_WAIT_SEC)
            if self.device_id is not None:
                print("Identity received")
                return True
        print("Identity not received, using broadcast")
        self.device_id = DEVICE_ID_BCAST
        return False

    def open_ports(
        self,
        in_portname="GT-1000:GT-1000 MIDI 1 24:0",
        out_portname="GT-1000:GT-1000 MIDI 1 24:0",
    ):
        try:
            self.midi_out, port_name = open_midioutput(out_portname)
        except (EOFError, KeyboardInterrupt):
            return False

        try:
            self.midi_in, port_name = open_midiinput(in_portname)
        except (EOFError, KeyboardInterrupt):
            return False
        # not sure if active_sense is useful yet
        self.midi_in.ignore_types(sysex=False, active_sense=False)
        self.midi_in.set_callback(MidiInputHandler(in_portname), self)
        return self.open_editor_mode()

    def fetch_mem(self, offset, length, override_checksum=None):
        self.send_message(self.assemble_message(RQ1_SYSEX_HEADER, offset + length, override_checksum))

    def set_byte(self, offset, data):
        self.send_message(self.assemble_message(DT1_SYSEX_HEADER, offset + data))

    def fetch_patch_names(self):
        self.fetch_mem(PATCH_NAMES_BEGIN_OFFSET, PATCH_NAMES_LEN)
        data = self.wait_recv_data()
        data_offset = 0
        for i in range(int(len(data[1])/16)):
            name = ""
            for j in range(16):
                name += chr(data[1][data_offset])
                data_offset += 1
            print(name)

    def open_editor_mode(self):
        # Device identification
        if not self.request_identity():
            return False
        # FIXME we don't compute the right checksum here for some reason, but the others are good
        self.fetch_mem(EDITOR_MODE_ADDRESS_FETCH1, EDITOR_MODE_ADDRESS_LEN1, [0])
        if not self.wait_state_change(2):
            return False

        self.set_byte(EDITOR_MODE_ADDRESS_SET2, EDITOR_MODE_ADDESS_VALUE2)
        if not self.wait_state_change(3):
            return False

        self.fetch_mem(EDITOR_MODE_ADDRESS_FETCH3, EDITOR_MODE_ADDRESS_LEN3)
        if not self.wait_state_change(4):
            return False
        return True

    def calculate_checksum(self, data):
        total = sum(data) % 128
        return [128 - total]

    def enable_fx(self, fx_id):
        msg = self.build_dt_message(
            self.base_address_pointers[f"live_fx{fx_id}"], f"fx{fx_id}", "FX SW", "ON"
        )
        return msg

    def disable_fx(self, fx_id):
        msg = self.build_dt_message(
            self.base_address_pointers[f"live_fx{fx_id}"], f"fx{fx_id}", "FX SW", "OFF"
        )
        return msg

    def send_message(self, message):
        # This whole thing is racy, but there is no real solution here
        self.received_data = None
        print(f"sending: {bytes_as_hex(message)}")
        self.midi_out.send_message(message)

    def _build_message(self, header, address_value, override_checksum=None):
        if override_checksum is not None:
            checksum = override_checksum
        else:
            checksum = self.calculate_checksum(address_value)
        # Override the broadcast address
        header[1] = self.device_id
        return SYSEX_START + header + address_value + checksum + SYSEX_END

    def build_dt_message(self, start_section, option, setting, param):
        address_value = self._construct_address_value(
            start_section, option, setting, param
        )
        return self._build_message(DT1_SYSEX_HEADER, address_value)

    def build_rq_message(self, start_address, length):
        address_value = start_address + length
        return self._build_message(RQ1_SYSEX_HEADER, address_value)

    def assemble_message(self, header, payload, override_checksum=None):
        return self._build_message(header, payload, override_checksum)

    def get_patch_names(self):
        self.send_message(self.build_rq_message(PATCH_NAMES_BEGIN_OFFSET, PATCH_NAMES_LEN))

    def wait_state_change(self, expected_state):
        for i in range(RETRY_COUNT):
            if self.current_state_message == expected_state:
                return True
            sleep(SLEEP_WAIT_SEC)
        return False

    def wait_recv_data(self):
        for i in range(RETRY_COUNT):
            if self.received_data is not None:
                return self.received_data
            sleep(SLEEP_WAIT_SEC)
        return None

    def _msg_editor_command1_reply(self, message):
        if len(message) != 15:
            return False

        # FIXME: again here we compute 0x80 but expect 0x79
        #expected_checksum = self.calculate_checksum(EDITOR_MODE_COMMAND1)
        expected_checksum = [0x79]
        expected_message = SYSEX_START + MANUFACTURER_ID + [self.device_id] + MODEL_ID + DT1_COMMAND_ID + EDITOR_REPLY1 + expected_checksum + SYSEX_END
        for i in range(len(message)):
            if message[i] != expected_message[i]:
                return False
        return True

    def _msg_editor_command2_reply(self, message):
        if len(message) != 15:
            return False

        expected_message = self.assemble_message(DT1_SYSEX_HEADER, EDITOR_MODE_ADDRESS_SET2 + EDITOR_MODE_ADDESS_VALUE2)
        for i in range(len(message)):
            if message[i] != expected_message[i]:
                return False
        return True

    def _msg_editor_command3_reply(self, message):
        if len(message) != 15:
            return False

        expected_checksum = self.calculate_checksum(EDITOR_REPLY3)
        expected_message = SYSEX_START + MANUFACTURER_ID + [self.device_id] + MODEL_ID + DT1_COMMAND_ID + EDITOR_REPLY3 + expected_checksum + SYSEX_END
        for i in range(len(message)):
            if message[i] != expected_message[i]:
                return False
        return True

    def _msg_identity_reply(self, message):
        # Byte Explanation
        # F0H: System Exclusive Message status
        # 7EH: ID Number (Universal Non-realtime Message)
        # dev: Device ID (dev: 00H - 1FH)
        # 06H: Sub ID # 1 (General Information)
        # 02H: Sub ID # 2 (Identity Reply)
        # 41H: Roland's manufacturer ID
        # 4FH,03H: Device family code (GT-1000/GT-1000CORE)
        # 00H,00H: Device family number code LSB, MSB
        # nnH: Software revision level # 1 (GT-1000:00H,GT-1000L:01H,GT-1000CORE:02H)
        # 00H: Software revision level # 2
        # vvH: Software revision level # 3 (GT-1000:01H,GT-1000L:01H,GT-1000CORE:00H)
        # 00H: Software revision level # 4
        # F7H: EOX (End of Exclusive)
        # 0xf0, 0x7e, 0x10, 0x6, 0x2, 0x41, 0x4f, 0x3, 0x0, 0x0, 0x2, 0x0, 0x0, 0x0, 0xf7
        if len(message) != 15:
            return False
        if (
            message[0] == SYSEX_START[0]
            and message[1] == NON_RT_MSG[0]
            and message[3] == GEN_INFO[0]
            and message[4] == IDENTITY_REPLY[0]
            and message[5] == MANUFACTURER_ID[0]
            and message[6] == GT1000_FAMILY[0]
            and message[7] == GT1000_FAMILY[1]
        ):
            device_id = message[2]
            software_rev_1 = message[10]
            software_rev_2 = message[12]
        else:
            return False
        if software_rev_1 == 0x00 and software_rev_2 == 0x01:
            print("GT-1000 detected")
            self.model = "GT-1000"
        elif software_rev_1 == 0x01 and software_rev_2 == 0x01:
            print("GT-1000L detected")
            self.model = "GT-1000L"
        elif software_rev_1 == 0x02 and software_rev_2 == 0x00:
            print("GT-1000CORE detected")
            self.model = "GT-1000CORE"
        self.device_id = device_id
        return True

    def process_received_message(self, message):
        print("receiving")
        # Process initial handshake as a state machine, the rest is just get/set
        if self.current_state_message is None and self._msg_identity_reply(message):
            self.current_state_message = 1
            print("identity ok")
            return
        elif self.current_state_message == 1 and self._msg_editor_command1_reply(message):
            print("command1 ok")
            self.current_state_message = 2
            return
        elif self.current_state_message == 2 and self._msg_editor_command2_reply(message):
            print("command2 ok")
            self.current_state_message = 3
            return
        elif self.current_state_message == 3 and self._msg_editor_command3_reply(message):
            print("command3 ok")
            self.current_state_message = 4
            return
        received_data_header = SYSEX_START + MANUFACTURER_ID + [self.device_id] + MODEL_ID + DT1_COMMAND_ID
        for i in range(len(received_data_header)):
            if message[i] != received_data_header[i]:
                print("Ignored received data")
                return
        received_offset = message[len(received_data_header):len(received_data_header)+4]
        # The actual data is after the header and before the checksum + SYSEX_END
        self.received_data = (received_offset, message[len(received_data_header) + 4:-2])
        print(f"data received: {self.received_data}")

    def _construct_address_value(self, start_section, option, setting, param):
        if start_section not in self.tables["base-addresses"]:
            print(f"Entry {start_section} missing in base-addresses")
            return None

        section_entry = self.tables["base-addresses"][start_section]
        address = bytes_to_int(section_entry["address"])

        option_entry = self.tables[section_entry["table"]][option]
        option_address_offset = bytes_to_int(option_entry["address"])

        setting_entry = self.tables[option_entry["table"]][setting]
        setting_address_offset = bytes_to_int(setting_entry["offset"])

        param_entry = setting_entry["values"][param]

        address += option_address_offset + setting_address_offset
        value = param_entry.to_bytes(1, byteorder="big")

        num_bytes = (address.bit_length() + 7) // 8
        byte_sequence = address.to_bytes(num_bytes, byteorder="big") + value
        byte_list = [byte for byte in byte_sequence]
        return byte_list


g = GT1000()
