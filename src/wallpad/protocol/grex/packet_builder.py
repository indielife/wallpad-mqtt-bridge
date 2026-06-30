from wallpad.devices.packet_builder import PacketBuilder
from wallpad.protocol.grex.constants import PREFIX_CONTROL_PACKET, PREFIX_RESPONSE_PACKET


class GrexPacketBuilder(PacketBuilder):
    """Grex 전열교환기 프로토콜에 맞추어 패킷 프레임을 조립하는 빌더입니다."""

    def build_control(self, mode_hex: str, speed_hex: str, postfix_hex: str) -> str:
        """컨트롤러에서 환기 본체로 보내는 제어 패킷을 조립합니다."""
        prefix = PREFIX_CONTROL_PACKET
        packet_without_checksum = prefix + mode_hex + speed_hex + postfix_hex
        checksum = self._calculate_checksum(packet_without_checksum, length=10)
        return packet_without_checksum + checksum

    def build_response(self, speed_hex: str, postfix_hex: str) -> str:
        """환기 본체에서 컨트롤러로 보내는 응답 패킷을 조립합니다."""
        prefix = PREFIX_RESPONSE_PACKET
        packet_without_checksum = prefix + speed_hex + postfix_hex
        checksum = self._calculate_checksum(packet_without_checksum, length=11)
        return packet_without_checksum + checksum

    def _calculate_checksum(self, packet: str, length: int) -> str:
        """첫 번째 바이트를 제외한 지정된 길이만큼의 바이트 합계를 구합니다."""
        bytes_data = bytearray.fromhex(packet)
        sum_buf = sum(bytes_data[1:length])
        return f"{(sum_buf % 256):02x}"
