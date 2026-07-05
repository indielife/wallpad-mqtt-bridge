import logging
from typing import ClassVar

from wallpad.protocol.base import PacketParser
from wallpad.protocol.kocom.constants import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    DEVICE_WALLPAD,
    KOCOM_COMMAND_BY_HEX,
    KOCOM_DEVICE_BY_HEX,
    KOCOM_FAN_SPEED_BY_HEX,
    KOCOM_TYPE_BY_HEX,
)

logger = logging.getLogger(__name__)


class KocomPacketParser(PacketParser):
    PACKET_FRAMES: ClassVar[dict[str, int]] = {"aa": 21}
    PACKET_LENGTH = 42

    def __init__(self, config) -> None:
        self._config = config

    def validate_checksum(self, packet: str) -> tuple[bool, str]:
        sum_packet = sum(bytearray.fromhex(packet)[:17])
        v_sum = int(packet[34:36], 16) if len(packet) >= 36 else 0
        chk_sum = f"{(sum_packet + 1 + v_sum) % 256:02x}"
        orgin_sum = packet[36:38] if len(packet) >= 38 else ""
        return (True, chk_sum) if chk_sum == orgin_sum else (False, chk_sum)

    def parse_frame(self, packet: str, device_states=None) -> dict | None:
        p = self._parse_packet(packet)
        if p is None:
            return None
        return self._value_packet(p, device_states)

    def _parse_packet(self, packet: str) -> dict | None:
        if len(packet) < self.PACKET_LENGTH:
            return None
        p: dict = {}
        try:
            p["header"] = packet[:4]
            p["type"] = packet[4:7]
            p["order"] = packet[7:8]
            if KOCOM_TYPE_BY_HEX.get(p["type"]) == "send":
                p["dst_device"] = packet[10:12]
                p["dst_room"] = packet[12:14]
                p["src_device"] = packet[14:16]
                p["src_room"] = packet[16:18]
            elif KOCOM_TYPE_BY_HEX.get(p["type"]) == "ack":
                p["src_device"] = packet[10:12]
                p["src_room"] = packet[12:14]
                p["dst_device"] = packet[14:16]
                p["dst_room"] = packet[16:18]
            else:
                return None
            p["command"] = packet[18:20]
            p["value"] = packet[20:36]
            p["checksum"] = packet[36:38]
            p["tail"] = packet[38:42]
            return p
        except Exception as e:
            logger.error("Failed to parse packet %s: %r", packet, e)
            return None

    def _value_packet(self, p: dict, device_states=None) -> dict | None:
        v: dict = {}
        try:
            v["type"] = KOCOM_TYPE_BY_HEX.get(p["type"])
            v["command"] = KOCOM_COMMAND_BY_HEX.get(p["command"])
            v["src_device"] = KOCOM_DEVICE_BY_HEX.get(p["src_device"])
            v["src_room"] = (
                self._config.kocom_room.get(p["src_room"])
                if v["src_device"] != DEVICE_THERMOSTAT
                else self._config.kocom_room_thermostat.get(p["src_room"])
            )
            v["dst_device"] = KOCOM_DEVICE_BY_HEX.get(p["dst_device"])
            v["dst_room"] = (
                self._config.kocom_room.get(p["dst_room"])
                if v["src_device"] != DEVICE_THERMOSTAT
                else self._config.kocom_room_thermostat.get(p["dst_room"])
            )
            v["value"] = p["value"]
            if v["src_device"] == DEVICE_FAN:
                v["value"] = self._parse_fan(p["value"])
            elif v["src_device"] in (DEVICE_LIGHT, DEVICE_PLUG):
                v["value"] = self._parse_switch(v["src_device"], v["src_room"], p["value"])
            elif v["src_device"] == DEVICE_THERMOSTAT:
                init_temp = False
                if device_states:
                    init_temp = (
                        device_states.get(DEVICE_THERMOSTAT, {})
                        .get(v["src_room"], {})
                        .get("target_temp", {})
                        .get("state", False)
                    )
                v["value"] = self._parse_thermostat(p["value"], init_temp)
            elif v["src_device"] == DEVICE_WALLPAD and v["dst_device"] == DEVICE_ELEVATOR:
                v["value"] = "off"
            elif v["src_device"] == DEVICE_GAS:
                v["value"] = v["command"]

            if (v["type"] == "ack" and v["dst_device"] == DEVICE_WALLPAD) or (
                v["type"] == "send" and v["dst_device"] == DEVICE_ELEVATOR
            ):
                if v["type"] == "send" and v["dst_device"] == DEVICE_ELEVATOR:
                    v["update_target"] = {
                        "device": v["dst_device"],
                        "room": DEVICE_WALLPAD,
                    }
                else:
                    v["update_target"] = {
                        "device": v["src_device"],
                        "room": DEVICE_WALLPAD
                        if v["src_device"] in (DEVICE_FAN, DEVICE_GAS)
                        else v["src_room"],
                    }

            return v
        except Exception as e:
            logger.error("Failed to interpret packet %r: %r", p, e)
            return None

    def _parse_fan(self, value: str) -> dict:
        return {
            "mode": "on" if value[:2] == "11" else "off",
            "speed": KOCOM_FAN_SPEED_BY_HEX.get(value[4:5]),
        }

    def _parse_switch(self, device: str, room: str, value: str) -> dict:
        switch: dict = {}
        on_count = 0
        to_i = (
            self._config.kocom_light_size.get(room, 0) + 1
            if device == DEVICE_LIGHT
            else self._config.kocom_plug_size.get(room, 0) + 1
        )
        for i in range(1, to_i):
            is_on = value[i * 2 - 2 : i * 2] != "00"
            switch[device + str(i)] = "on" if is_on else "off"
            if is_on:
                on_count += 1
        switch[device + "0"] = "on" if on_count > 0 else "off"
        return switch

    def _parse_thermostat(self, value: str, init_temp=False) -> dict:
        thermo: dict = {}
        heat_mode = "heat" if value[:2] == "11" else "off"
        away_mode = value[2:4] == "01"
        thermo["current_temp"] = int(value[8:10], 16)
        if heat_mode == "heat" and away_mode:
            thermo["mode"] = "fan_only"
            thermo["target_temp"] = self._config.init_temp if not init_temp else int(init_temp)
        elif heat_mode == "heat":
            thermo["mode"] = "heat"
            thermo["target_temp"] = int(value[4:6], 16)
        else:
            thermo["mode"] = "off"
            thermo["target_temp"] = self._config.init_temp if not init_temp else int(init_temp)
        return thermo
