class PacketBuilder:
    """
    패킷 생성을 위한 템플릿(전략) 인터페이스입니다.
    각 프로토콜(Kocom, Grex 등)에 맞는 빌더가 이를 상속받아 구현합니다.
    """

    def build(
        self, device_hex: str, room_hex: str, dst_hex: str, cmd_hex: str, value_hex: str
    ) -> str:
        raise NotImplementedError
