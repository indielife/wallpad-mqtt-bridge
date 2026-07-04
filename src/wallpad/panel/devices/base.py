from wallpad.devices.base import BaseDevice
from wallpad.devices.packet_builder import PacketBuilder
from wallpad.devices.topic import TopicContext
from wallpad.protocol.base import HardwareInfo


class PanelDevice(BaseDevice):
    """월패드 패널 기기들이 공유하는 식별자·메타데이터 기반 클래스입니다."""

    def __init__(
        self,
        name_prefix: str,
        room: str,
        sub_device: str,
        sw_version: str,
        hardware_info: HardwareInfo,
        packet_builder: PacketBuilder | None = None,
        topics: TopicContext | None = None,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device=sub_device,
            sw_version=sw_version,
            hardware_info=hardware_info,
            packet_builder=packet_builder,
            topics=topics,
        )
