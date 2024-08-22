#!/usr/bin/env python3

import json
import rtmidi
import time
import sys
import threading
import logging
from time import sleep
from datetime import datetime
from rtmidi.midiutil import open_midiinput, open_midioutput
from pathlib import Path

from .constants import (
    SYSEX_END,
    MODEL_ID,
    PATCH_NAMES_LEN,
    EDITOR_REPLY1,
    EDITOR_REPLY2,
    EDITOR_REPLY3,
    DEVICE_ID_BCAST,
    PATCH_NAMES_BEGIN_OFFSET,
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

MIDI_PORT = "GT-1000:GT-1000 MIDI 1"
SLEEP_WAIT_SEC = 0.1
REFRESH_STATE_POLL_RATE_SEC = 5
RETRY_COUNT = 100

logging.basicConfig(
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        logger.debug(
            f"[%s] @%0.6f %s" % (self.port, self._wallclock, bytes_as_hex(message))
        )
        gt1000.process_received_message(message)


class GT1000:
    def __init__(self):
        self.tables = {}
        self.device_id = DEVICE_ID_BCAST
        self.current_state_message = None
        self.received_data = {}
        self.data_semaphore = threading.Semaphore(1)
        self.stop = False

        # Protect current_state and prevent state changes while refreshing
        self.state_lock = threading.Semaphore(1)
        # The known state of the effects
        self.current_state = {"last_sync_ts": {}}

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
        logger.info("GT1000 instance created")

    def start_refresh_thread(self):
        """Background thread to refresh the known device state"""
        self.refresh_thread = threading.Thread(target=self.refresh_state_thread)
        self.refresh_thread.start()

    def stop_refresh_thread(self):
        self.stop = True

    def refresh_state(self):
        with self.state_lock:
            logger.debug("Refresh state")
            self.current_state["fx"] = self.get_all_fx_names_state()
            self.current_state["last_sync_ts"]["fx"] = datetime.now()

    def get_state(self):
        with self.state_lock:
            return self.current_state

    def refresh_state_thread(self):
        while not self.stop:
            for i in range(10):
                if self.stop:
                    return
                time.sleep(REFRESH_STATE_POLL_RATE_SEC / 10)
            self.refresh_state()

    def request_identity(self):
        # TODO: this should be a background thread so we update the ID if the
        # device comes online at some point
        for i in range(RETRY_COUNT):
            self.send_message(IDENTITY_REQUEST_MSG)
            sleep(SLEEP_WAIT_SEC)
            if self.device_id != DEVICE_ID_BCAST:
                logger.info(
                    f"Identity received: {self.device_id} ({hex(self.device_id)})"
                )
                return True
        logger.warning(
            f"Identity not received, using broadcast {self.device_id} ({hex(self.device_id)})"
        )
        return False

    def _get_midi_exact_port_names(self, portname):
        """The portname usually contains an ID that can change depending on the other devices"""
        tmp_midi_out = rtmidi.MidiOut()
        port_count = tmp_midi_out.get_port_count()
        out_portname = None
        for i in range(port_count):
            if tmp_midi_out.get_port_name(i).startswith(portname):
                out_portname = tmp_midi_out.get_port_name(i)

        tmp_midi_in = rtmidi.MidiIn()
        port_count = tmp_midi_in.get_port_count()
        in_portname = None
        for i in range(port_count):
            if tmp_midi_in.get_port_name(i).startswith(portname):
                in_portname = tmp_midi_in.get_port_name(i)
        if in_portname is None:
            logger.error(
                f"Failed to find MIDI input port starting with {portname}. Found {tmp_midi_in.get_ports()}"
            )

        if out_portname is None:
            logger.error(
                f"Failed to find MIDI output port starting with {portname}. Found {tmp_midi_out.get_ports()}"
            )
        return in_portname, out_portname

    def open_ports(self, portname=MIDI_PORT):
        in_portname, out_portname = self._get_midi_exact_port_names(portname)
        if in_portname is None or out_portname is None:
            return False
        try:
            self.midi_out, port_name = open_midioutput(out_portname)
        except (EOFError, KeyboardInterrupt):
            return False

        try:
            self.midi_in, port_name = open_midiinput(in_portname)
        except (EOFError, KeyboardInterrupt):
            return False
        self.midi_in.ignore_types(sysex=False)
        self.midi_in.set_callback(MidiInputHandler(in_portname), self)
        return self.open_editor_mode()

    def _get_fx_name(self, fx_id):
        offset = self._construct_address_value(
            self.base_address_pointers[f"live_fx{fx_id}"],
            f"fx{fx_id}",
            "FX1 TYPE",
            None,
        )
        data = self.fetch_mem(offset, [0x0, 0x0, 0x0, 0x1])
        if data is None:
            logger.warning(f"_get_fx_name no data for fx {fx_id}")
            return None
        for i in self.tables["PatchFx"]["FX1 TYPE"]["values"]:
            if data[0] == self.tables["PatchFx"]["FX1 TYPE"]["values"][i]:
                if i == "AC RESONANCE":
                    xxx
                return i
        return None

    def _get_fx_state(self, fx_id):
        offset = self._construct_address_value(
            self.base_address_pointers[f"live_fx{fx_id}"], f"fx{fx_id}", "FX SW", None
        )
        data = self.fetch_mem(offset, [0x0, 0x0, 0x0, 0x1])
        if data is None:
            logger.warning(f"_get_fx_bypass no data for fx {fx_id} bypass")
            return None
        for i in self.tables["PatchFx"]["FX SW"]["values"]:
            if data[0] == self.tables["PatchFx"]["FX SW"]["values"][i]:
                return i
        return None

    def get_one_fx_name_state(self, fx_id):
        name = self._get_fx_name(fx_id)
        state = self._get_fx_state(fx_id)
        return {"fx_id": fx_id, "name": name, "state": state}

    def get_all_fx_names_state(self):
        logger.debug("get_all_fx_names_state")
        if self.model == "GT-1000CORE":
            nr_fx = 3
        else:
            nr_fx = 4

        effects = []
        for i in range(nr_fx):
            fx_id = i + 1
            effects.append(self.get_one_fx_name_state(fx_id))
        return effects

    def fetch_mem(self, offset, length, override_checksum=None):
        self.send_message(
            self.assemble_message(RQ1_SYSEX_HEADER, offset + length, override_checksum),
            offset=offset,
        )
        return self.wait_recv_data(offset)

    def set_byte(self, offset, data):
        self.send_message(self.assemble_message(DT1_SYSEX_HEADER, offset + data), offset)

    def fetch_patch_names(self):
        data = self.fetch_mem(PATCH_NAMES_BEGIN_OFFSET, PATCH_NAMES_LEN)
        data_offset = 0
        names = []
        # We would need to iterate over more base offsets to get the whole
        # list, unused for now but left as an example.
        for i in range(int(len(data[1]) / 16)):
            name = ""
            for j in range(16):
                name += chr(data[1][data_offset])
                data_offset += 1
            names.append(name)
        return name

    def open_editor_mode(self):
        logger.info("Opening device in editor mode")
        # Device identification
        if not self.request_identity():
            return False
        # The 2 fetch operations here may break if the value returned changes at some point.
        # Not sure what is the point of those, it looks like a simple check to make sure the
        # device is responsive.

        # FIXME we don't compute the right checksum here for some reason, but the others are good
        data = self.fetch_mem(EDITOR_MODE_ADDRESS_FETCH1, EDITOR_MODE_ADDRESS_LEN1, [0])
        if data != EDITOR_REPLY1:
            return False
        logger.debug("command1 ok")

        self.set_byte(EDITOR_MODE_ADDRESS_SET2, EDITOR_MODE_ADDESS_VALUE2)
        data = self.wait_recv_data(EDITOR_MODE_ADDRESS_SET2)
        if data != EDITOR_REPLY2:
            return False
        logger.debug("command2 ok")

        data = self.fetch_mem(EDITOR_MODE_ADDRESS_FETCH3, EDITOR_MODE_ADDRESS_LEN3)
        if data != EDITOR_REPLY3:
            return False
        logger.debug("command3 ok")
        logger.info("Device opened in editor mode")
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

    def send_message(self, message, offset=None):
        with self.data_semaphore:
            self.received_data[str(offset)] = None
            logger.debug(f"sending: {bytes_as_hex(message)}")
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
        self.send_message(
            self.build_rq_message(PATCH_NAMES_BEGIN_OFFSET, PATCH_NAMES_LEN)
        )

    def wait_recv_data(self, offset=None):
        for i in range(RETRY_COUNT):
            with self.data_semaphore:
                if self.received_data[str(offset)] is not None:
                    return self.received_data[str(offset)]
            sleep(SLEEP_WAIT_SEC)
        return None

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
            # message[2] is the identity
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
            logger.info("GT-1000 detected")
            self.model = "GT-1000"
        elif software_rev_1 == 0x01 and software_rev_2 == 0x01:
            logger.info("GT-1000L detected")
            self.model = "GT-1000L"
        elif software_rev_1 == 0x02 and software_rev_2 == 0x00:
            logger.info("GT-1000CORE detected")
            self.model = "GT-1000CORE"
        self.device_id = device_id
        return True

    def process_received_message(self, message):
        logger.debug("receiving")
        if self.device_id == DEVICE_ID_BCAST and self._msg_identity_reply(message):
            logger.debug("identity ok")
            return
        received_data_header = (
            SYSEX_START + MANUFACTURER_ID + [self.device_id] + MODEL_ID + DT1_COMMAND_ID
        )
        for i in range(len(received_data_header)):
            if message[i] != received_data_header[i]:
                logger.debug("Ignored received data")
                return
        received_offset = message[
            len(received_data_header) : len(received_data_header) + 4
        ]
        # The actual data is after the header and before the checksum + SYSEX_END
        self.received_data[str(received_offset)] = message[
            len(received_data_header) + 4 : -2
        ]
        logger.debug(
            f"data received: {self.received_data[str(received_offset)]} for offset {received_offset}"
        )

    def _construct_address_value(self, start_section, option, setting, param):
        # param is the setting we want to set, if None we just contruct the base address
        if start_section not in self.tables["base-addresses"]:
            logger.error(f"Entry {start_section} missing in base-addresses")
            return None

        section_entry = self.tables["base-addresses"][start_section]
        address = bytes_to_int(section_entry["address"])

        option_entry = self.tables[section_entry["table"]][option]
        option_address_offset = bytes_to_int(option_entry["address"])

        setting_entry = self.tables[option_entry["table"]][setting]
        setting_address_offset = bytes_to_int(setting_entry["offset"])

        address += option_address_offset + setting_address_offset
        if param is None:
            num_bytes = (address.bit_length() + 7) // 8
            byte_sequence = address.to_bytes(num_bytes, byteorder="big")
            byte_list = [byte for byte in byte_sequence]
            return byte_list

        param_entry = setting_entry["values"][param]

        value = param_entry.to_bytes(1, byteorder="big")

        num_bytes = (address.bit_length() + 7) // 8
        byte_sequence = address.to_bytes(num_bytes, byteorder="big") + value
        byte_list = [byte for byte in byte_sequence]
        return byte_list
