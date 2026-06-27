from wallpad.devices.packet_builder import PacketBuilder
from wallpad.protocol.kocom.constants import KOCOM_COMMAND_REV, KOCOM_DEVICE_REV


class KocomPacketBuilder(PacketBuilder):
    """Kocom RS485 프로토콜에 맞추어 패킷 프레임을 조립하는 빌더입니다."""

    HEADER = "aa5530bc00"
    TAIL = "0d0d"

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

    def build_scan_packet(
        self,
        device: str,
        room: str,
        room_rev: dict,
        room_thermostat_rev: dict,
    ) -> str:
        """기기 상태 조회를 위한 스캔(조회) 패킷을 생성합니다."""
        device_hex = KOCOM_DEVICE_REV.get(device, "")
        room_hex = (
            room_rev.get(room, "") if device != "thermostat" else room_thermostat_rev.get(room, "")
        )
        dst_hex = KOCOM_DEVICE_REV.get("wallpad", "01") + room_rev.get("wallpad", "00")
        cmd_hex = KOCOM_COMMAND_REV.get("조회", "3a")
        value_hex = "0000000000000000"
        return self.build(
            device_hex=device_hex,
            room_hex=room_hex,
            dst_hex=dst_hex,
            cmd_hex=cmd_hex,
            value_hex=value_hex,
        )
