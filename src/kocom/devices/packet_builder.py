class PacketBuilder:
    """
    패킷 생성을 위한 템플릿(전략) 인터페이스입니다.
    각 프로토콜(Kocom, Grex 등)에 맞는 빌더가 이를 상속받아 구현합니다.
    """

    def build(self, **kwargs) -> str:
        raise NotImplementedError


class KocomPacketBuilder(PacketBuilder):
    """Kocom RS485 프로토콜에 맞추어 패킷 프레임을 조립하는 빌더입니다."""

    HEADER = "aa5530bc00"
    TAIL = "0d0d"

    def build(self, device: str, room: str, dst: str, cmd: str, value: str) -> str:
        """주어진 부품들을 Kocom 프레임(헤더, 페이로드, 체크섬, 테일)으로 조립합니다."""
        if not (device and room and dst and cmd and value):
            return ""

        payload = device + room + dst + cmd + value
        packet_without_checksum = self.HEADER + payload
        chk_sum = self._calculate_checksum(packet_without_checksum)

        return packet_without_checksum + chk_sum + self.TAIL

    def _calculate_checksum(self, packet: str) -> str:
        sum_packet = sum(bytearray.fromhex(packet)[:17])
        v_sum = int(packet[34:36], 16) if len(packet) >= 36 else 0
        return f"{(sum_packet + 1 + v_sum) % 256:02x}"
