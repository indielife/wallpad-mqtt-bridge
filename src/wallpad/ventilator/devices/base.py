from wallpad.devices.base import BaseDevice
from wallpad.protocol.grex import constants as grex_const
from wallpad.protocol.grex.packet_builder import GrexPacketBuilder


class VentilatorDevice(BaseDevice):
    """환기장치 기기들이 공유하는 식별자·메타데이터 기반 클래스입니다."""

    def __init__(
        self,
        sw_version: str,
        name_prefix: str = "grex",
        packet_builder: GrexPacketBuilder | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room="grex",
            sub_device="fan",
            sw_version=sw_version,
            packet_builder=packet_builder,
        )

    @property
    def device_info(self) -> dict:
        """Grex 고유의 기기 메타데이터를 반환합니다."""
        return {
            "name": f"{grex_const.NAME_PREFIX} Ventilator",
            "identifiers": f"{grex_const.IDENTIFIER_PREFIX}_ventilator",
            "manufacturer": grex_const.MANUFACTURER,
            "model": grex_const.MODEL,
            "sw_version": self.sw_version,
        }
