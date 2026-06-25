from wallpad.protocol.base import PacketParser
from wallpad.protocol.grex.constants import MODE, SPEED

_CHECKSUM_LENGTH = {"d08a": 10, "d18b": 11, "d00a": 10}


class GrexPacketParser(PacketParser):
    def validate_checksum(self, packet: str) -> tuple[bool, str]:
        length = _CHECKSUM_LENGTH.get(packet[:4], 10)
        hex_list = self._hex_to_list(packet)
        sum_buf = sum(int(x, 16) for x in hex_list[1:length])
        chksum_hex = f"0x{(sum_buf % 256):02x}"
        result_hex = hex_list[length] if len(hex_list) > length else "0x00"
        return (result_hex == chksum_hex, result_hex)

    def parse_frame(self, packet: str) -> dict:
        prefix = packet[:4]
        if prefix == "d08a":
            return self._parse_d08a(packet)
        if prefix == "d18b":
            return self._parse_d18b(packet)
        return {"prefix": prefix}

    def _hex_to_list(self, hex_string: str) -> list:
        return [f"0x{hex_string[i:i + 2].lower()}" for i in range(0, len(hex_string), 2)]

    def _parse_d08a(self, packet: str) -> dict:
        return {
            "prefix": "d08a",
            "mode": MODE.get(packet[8:12]),
            "speed": SPEED.get(packet[12:16]),
        }

    def _parse_d18b(self, packet: str) -> dict:
        return {
            "prefix": "d18b",
            "speed": SPEED.get(packet[8:12]),
        }
