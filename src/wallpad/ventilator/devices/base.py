from wallpad.devices.base import BaseDevice
from wallpad.protocol.base import HardwareInfo
from wallpad.protocol.grex.packet_builder import GrexPacketBuilder


class VentilatorDevice(BaseDevice):
    """환기장치 기기들이 공유하는 식별자·메타데이터 기반 클래스입니다."""

    def __init__(
        self,
        sw_version: str,
        hw_info: HardwareInfo,
        name_prefix: str = "grex",
        packet_builder: GrexPacketBuilder | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room="grex",
            sub_device="fan",
            sw_version=sw_version,
            hw_info=hw_info,
            packet_builder=packet_builder,
        )

    @property
    def device_info(self) -> dict:
        """환기장치 기기 고유의 메타데이터를 반환합니다."""
        hw = self.hw_info
        return {
            "name": f"{hw.name_prefix} {hw.model}",
            "identifiers": f"{hw.identifier_prefix}_{hw.model.lower()}",
            "manufacturer": hw.manufacturer,
            "model": hw.model,
            "sw_version": self.sw_version,
        }
