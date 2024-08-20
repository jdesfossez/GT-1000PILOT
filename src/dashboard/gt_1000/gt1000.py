#!/usr/bin/env python3

import json
import rtmidi
import time
from rtmidi.midiutil import open_midiinput, open_midioutput
from pathlib import Path

from .constants import SYSEX_END, SYSEX_HEADER, SYSEX_START



def bytes_to_int(value):
    return int.from_bytes(value, byteorder="big")


def bytes_as_hex(data):
    return("[{}]".format(", ".join(hex(x) for x in data)))


class MidiInputHandler(object):
    def __init__(self, port):
        self.port = port
        self._wallclock = time.time()

    def __call__(self, event, data=None):
        message, deltatime = event
        self._wallclock += deltatime
        print(f"[%s] @%0.6f %r {data.midi_in}" % (self.port, self._wallclock, message))

def receive_midi_message_cb(data, gt1000):
    #print("IN", data, gt1000.midi_in)
    print("IN", data, gt1000)


class GT1000:
    def __init__(self):
        self.tables = {}
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

#        msg = self.get_message(
#            self.base_address_pointers["live_fx1"], "fx1", "FX1 TYPE", "DEFRETTER"
#        )
#        print_has_hex(msg)
#        msg = self.get_message(
#            self.base_address_pointers["live_fx3"], "fx3", "FX1 TYPE", "FLANGER"
#        )
#        print_has_hex(msg)

    def open_ports(self, portname="GT-1000:GT-1000 MIDI 1 24:0"):
        try:
            self.midi_out, port_name = open_midioutput(portname)
        except (EOFError, KeyboardInterrupt):
            return False

        try:
            self.midi_in, port_name = open_midiinput(portname)
        except (EOFError, KeyboardInterrupt):
            return False
        self.midi_in.ignore_types(sysex=False)
        self.midi_in.set_callback(MidiInputHandler(portname), self)
        # Device identification
        self.send_message([0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7])
        return True

    def calculate_checksum(self, data):
        total = sum(data) % 128
        return [128 - total]


    def enable_fx(self, fx_id):
        msg = self.get_message(
            self.base_address_pointers[f"live_fx{fx_id}"], f"fx{fx_id}", "FX SW", "ON"
        )
        return msg

    def disable_fx(self, fx_id):
        msg = self.get_message(
            self.base_address_pointers[f"live_fx{fx_id}"], f"fx{fx_id}", "FX SW", "OFF"
        )
        return msg

    def send_message(self, message):
        print(f"sending: {bytes_as_hex(message)}")
        self.midi_out.send_message(message)

    def get_message(self, start_section, option, setting, param):
        address_value = self._construct_address_value(
            start_section, option, setting, param
        )
        checksum = self.calculate_checksum(address_value)
        return SYSEX_START + SYSEX_HEADER + address_value + checksum + SYSEX_END

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
