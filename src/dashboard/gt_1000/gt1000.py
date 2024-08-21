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
    EDITOR_MODE_COMMAND1,
    EDITOR_MODE_COMMAND2,
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


def receive_midi_message_cb(data, gt1000):
    # print("IN", data, gt1000.midi_in)
    print("IN", data, gt1000)


class GT1000:
    def __init__(self):
        self.tables = {}
        self.device_id = None
        self.current_state_message = None
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
        for i in range(6):
            self.send_message(IDENTITY_REQUEST_MSG)
            sleep(1)
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
        # Device identification
        if not self.request_identity():
            return False
        if not self.send_editor_command_wait_state_change(EDITOR_MODE_COMMAND1, [0], 2):
            return False
        # FIXME: DT
        if not self.send_editor_command_wait_state_change(EDITOR_MODE_COMMAND2, None, 2, DT=True):
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

    def build_rq_message_from_code(self, code, override_checksum=None, DT=False):
        # These don't look like address + offset queries, maybe they are, but it's
        # not understood yet.
        if DT:
            return self._build_message(DT1_SYSEX_HEADER, code, override_checksum)
        return self._build_message(RQ1_SYSEX_HEADER, code, override_checksum)

    def get_patch_names(self):
        self.send_message(self.build_rq_message(PATCH_NAMES_BEGIN_OFFSET, PATCH_NAMES_LEN))

    def send_editor_command_wait_state_change(self, command, override_checksum, expected_state, DT=False):
        self.send_message(self.build_rq_message_from_code(command, override_checksum, DT))
        for i in range(10):
            if self.current_state_message == expected_state:
                return True
            sleep(1)
        return False

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
            print("%x matches" % message[i])
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
        if self.current_state_message is None and self._msg_identity_reply(message):
            self.current_state_message = 1
            print("identity ok")
            return
        elif self.current_state_message == 1 and self._msg_editor_command1_reply(message):
            print("command1 ok")
            self.current_state_message = 2
            return

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
