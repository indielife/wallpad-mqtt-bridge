from wallpad.protocol.base import PacketParser
from wallpad.protocol.kocom.constants import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    DEVICE_WALLPAD,
    KOCOM_COMMAND,
    KOCOM_DEVICE,
    KOCOM_FAN_SPEED,
    KOCOM_TYPE,
)


class KocomPacketParser(PacketParser):
    def __init__(
        self,
        room: dict,
        room_thermostat: dict,
        light_size: dict,
        plug_size: dict,
        init_temp: int,
    ) -> None:
        self._room = room
        self._room_thermostat = room_thermostat
        self._light_size = light_size
        self._plug_size = plug_size
        self._init_temp = init_temp

    def validate_checksum(self, packet: str) -> tuple[bool, str]:
        sum_packet = sum(bytearray.fromhex(packet)[:17])
        v_sum = int(packet[34:36], 16) if len(packet) >= 36 else 0
        chk_sum = f"{(sum_packet + 1 + v_sum) % 256:02x}"
        origin_sum = packet[36:38] if len(packet) >= 38 else ""
        return (chk_sum == origin_sum, chk_sum)

    def parse_frame(self, packet: str) -> dict:
        p: dict = {}
        try:
            p["header"] = packet[:4]
            p["type"] = packet[4:7]
            p["order"] = packet[7:8]
            if KOCOM_TYPE.get(p["type"]) == "send":
                p["dst_device"] = packet[10:12]
                p["dst_room"] = packet[12:14]
                p["src_device"] = packet[14:16]
                p["src_room"] = packet[16:18]
            elif KOCOM_TYPE.get(p["type"]) == "ack":
                p["src_device"] = packet[10:12]
                p["src_room"] = packet[12:14]
                p["dst_device"] = packet[14:16]
                p["dst_room"] = packet[16:18]
            p["command"] = packet[18:20]
            p["value"] = packet[20:36]
            p["checksum"] = packet[36:38]
            p["tail"] = packet[38:42]
        except Exception:
            return {}
        return p

    def parse(self, packet: str, device_states: dict | None = None) -> dict | None:
        frame = self.parse_frame(packet)
        if not frame:
            return None
        return self._map_values(frame, device_states)

    def _map_values(self, p: dict, device_states: dict | None = None) -> dict | None:
        v: dict = {}
        try:
            v["type"] = KOCOM_TYPE.get(p["type"])
            v["command"] = KOCOM_COMMAND.get(p["command"])
            v["src_device"] = KOCOM_DEVICE.get(p.get("src_device", ""))
            src_room_hex = p.get("src_room", "")
            v["src_room"] = (
                self._room_thermostat.get(src_room_hex)
                if v["src_device"] == DEVICE_THERMOSTAT
                else self._room.get(src_room_hex)
            )
            v["dst_device"] = KOCOM_DEVICE.get(p.get("dst_device", ""))
            dst_room_hex = p.get("dst_room", "")
            v["dst_room"] = (
                self._room_thermostat.get(dst_room_hex)
                if v["src_device"] == DEVICE_THERMOSTAT
                else self._room.get(dst_room_hex)
            )
            v["value"] = p["value"]
            if v["src_device"] == DEVICE_FAN:
                v["value"] = self._parse_fan_value(p["value"])
            elif v["src_device"] in (DEVICE_LIGHT, DEVICE_PLUG):
                v["value"] = self._parse_switch_value(v["src_device"], v["src_room"], p["value"])
            elif v["src_device"] == DEVICE_THERMOSTAT:
                init_temp = None
                if device_states:
                    room_state = device_states.get(DEVICE_THERMOSTAT, {}).get(v["src_room"], {})
                    init_temp = room_state.get("target_temp", {}).get("state")
                v["value"] = self._parse_thermostat_value(p["value"], init_temp)
            elif v["src_device"] == DEVICE_WALLPAD and v["dst_device"] == DEVICE_ELEVATOR:
                v["value"] = "off"
            elif v["src_device"] == DEVICE_GAS:
                v["value"] = v["command"]
        except Exception:
            return None
        return v

    def _parse_fan_value(self, value: str) -> dict:
        return {
            "mode": "on" if value[:2] == "11" else "off",
            "speed": KOCOM_FAN_SPEED.get(value[4:5]),
        }

    def _parse_switch_value(self, device: str, room: str, value: str) -> dict:
        switch: dict = {}
        on_count = 0
        count = (
            self._light_size.get(room, 0)
            if device == DEVICE_LIGHT
            else self._plug_size.get(room, 0)
        )
        for i in range(1, count + 1):
            switch[device + str(i)] = "off" if value[i * 2 - 2 : i * 2] == "00" else "on"
            if value[i * 2 - 2 : i * 2] != "00":
                on_count += 1
        switch[device + "0"] = "on" if on_count > 0 else "off"
        return switch

    def _parse_thermostat_value(self, value: str, init_temp=None) -> dict:
        thermo: dict = {}
        heat_mode = "heat" if value[:2] == "11" else "off"
        away_mode = "on" if value[2:4] == "01" else "off"
        thermo["current_temp"] = int(value[8:10], 16)
        effective_init = int(init_temp) if init_temp else self._init_temp
        if heat_mode == "heat" and away_mode == "on":
            thermo["mode"] = "fan_only"
            thermo["target_temp"] = effective_init
        elif heat_mode == "heat" and away_mode == "off":
            thermo["mode"] = "heat"
            thermo["target_temp"] = int(value[4:6], 16)
        elif heat_mode == "off":
            thermo["mode"] = "off"
            thermo["target_temp"] = effective_init
        return thermo
