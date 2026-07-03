from wallpad.devices.packet_builder import PacketBuilder
from wallpad.protocol.kocom.constants import KOCOM_HEX_BY_COMMAND, KOCOM_HEX_BY_DEVICE


class KocomPacketBuilder(PacketBuilder):
    """Kocom RS485 프로토콜에 맞추어 패킷 프레임을 조립하는 빌더입니다."""

    HEADER = "aa5530bc00"
    TAIL = "0d0d"

    def __init__(self, room_rev: dict | None = None, room_thermostat_rev: dict | None = None):
        self.room_rev = room_rev or {}
        self.room_thermostat_rev = room_thermostat_rev or {}

    def encode(self, *, src: str, dst: str, room: str, cmd: str, value_hex: str) -> str:
        """기기 이름과 방 이름으로 Kocom 주소·명령 니블을 조립해 패킷을 생성합니다."""
        device_hex = KOCOM_HEX_BY_DEVICE.get(src, "")
        room_hex = (
            self.room_thermostat_rev.get(room, "")
            if src == "thermostat"
            else self.room_rev.get(room, "")
        )
        dst_hex = KOCOM_HEX_BY_DEVICE.get(dst, "") + self.room_rev.get("wallpad", "")
        cmd_hex = KOCOM_HEX_BY_COMMAND.get(cmd, "")
        return self.build(
            device_hex=device_hex,
            room_hex=room_hex,
            dst_hex=dst_hex,
            cmd_hex=cmd_hex,
            value_hex=value_hex,
        )

    def build(
        self, device_hex: str, room_hex: str, dst_hex: str, cmd_hex: str, value_hex: str
    ) -> str:
        """주어진 부품들을 Kocom 프레임(헤더, 페이로드, 체크섬, 테일)으로 조립합니다."""
        if not (device_hex and room_hex and dst_hex and cmd_hex and value_hex):
            return ""

        payload = device_hex + room_hex + dst_hex + cmd_hex + value_hex
        packet_without_checksum = self.HEADER + payload
        checksum = self._calculate_checksum(packet_without_checksum)

        return packet_without_checksum + checksum + self.TAIL

    def _calculate_checksum(self, packet: str) -> str:
        sum_packet = sum(bytearray.fromhex(packet)[:17])
        v_sum = int(packet[34:36], 16) if len(packet) >= 36 else 0
        return f"{(sum_packet + 1 + v_sum) % 256:02x}"

    def build_scan_packet(self, device: str, room: str) -> str:
        """기기 상태 조회를 위한 스캔(조회) 패킷을 생성합니다."""
        return self.encode(
            src=device,
            dst="wallpad",
            room=room,
            cmd="조회",
            value_hex="0000000000000000",
        )
