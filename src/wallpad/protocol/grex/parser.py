from wallpad.protocol.base import PacketParser
from wallpad.protocol.grex.constants import MODE, SPEED


class GrexPacketParser(PacketParser):
    def validate_checksum(self, packet: str) -> tuple[bool, str]:
        n = len(packet) // 2
        length = n - 1
        sum_buf = sum(int(packet[i * 2 : i * 2 + 2], 16) for i in range(1, length))
        chk = f"{sum_buf % 256:02x}"
        actual = packet[length * 2 : length * 2 + 2].lower()
        return (True, chk) if chk == actual else (False, chk)

    def parse_frame(self, packet: str) -> dict | None:
        p_prefix = packet[:4]
        if p_prefix == "d00a":
            return {"type": "d00a"}
        if p_prefix == "d08a":
            return {
                "type": "d08a",
                "mode": MODE.get(packet[8:12]),
                "speed": SPEED.get(packet[12:16]),
            }
        if p_prefix == "d18b":
            return {
                "type": "d18b",
                "speed": SPEED.get(packet[8:12]),
            }
        return None
