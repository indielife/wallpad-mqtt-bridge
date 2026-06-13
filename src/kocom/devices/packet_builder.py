class PacketBuilder:
    """
    패킷 생성을 위한 템플릿(전략) 인터페이스입니다.
    각 프로토콜(Kocom, Grex 등)에 맞는 빌더가 이를 상속받아 구현합니다.
    """

    def build(
        self, device_hex: str, room_hex: str, dst_hex: str, cmd_hex: str, value_hex: str
    ) -> str:
        raise NotImplementedError


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
