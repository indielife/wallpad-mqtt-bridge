from typing import ClassVar

from wallpad.protocol.base import PacketParser
from wallpad.protocol.grex.constants import (
    MODE,
    PREFIX_CONTROLLER_ERROR,
    PREFIX_CONTROLLER_STATUS,
    PREFIX_VENTILATOR_STATUS,
    SPEED,
)


class GrexPacketParser(PacketParser):
    SOF_LENGTH_MAP: ClassVar[dict[str, int]] = {"d00a": 11, "d08a": 11, "d18b": 12}

    def validate_checksum(self, packet: str) -> tuple[bool, str]:
        n = len(packet) // 2
        length = n - 1
        sum_buf = sum(int(packet[i * 2 : i * 2 + 2], 16) for i in range(1, length))
        chk = f"{sum_buf % 256:02x}"
        actual = packet[length * 2 : length * 2 + 2].lower()
        return (True, chk) if chk == actual else (False, chk)

    def parse_frame(self, packet: str) -> dict | None:
        p_prefix = packet[:4]
        if p_prefix == PREFIX_CONTROLLER_ERROR:
            return {"type": PREFIX_CONTROLLER_ERROR}
        if p_prefix == PREFIX_CONTROLLER_STATUS:
            return {
                "type": PREFIX_CONTROLLER_STATUS,
                "mode": MODE.get(packet[8:12]),
                "speed": SPEED.get(packet[12:16]),
            }
        if p_prefix == PREFIX_VENTILATOR_STATUS:
            return {
                "type": PREFIX_VENTILATOR_STATUS,
                "speed": SPEED.get(packet[8:12]),
            }
        return None
