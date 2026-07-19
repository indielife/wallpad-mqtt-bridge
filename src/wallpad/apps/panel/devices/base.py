from wallpad.devices.base import BaseDevice
from wallpad.devices.topic import TopicContext
from wallpad.protocol.base import HardwareInfo


class PanelDevice(BaseDevice):
    """월패드 패널 기기들이 공유하는 식별자·메타데이터 기반 클래스입니다."""

    topics: TopicContext

    def __init__(
        self,
        name_prefix: str,
        room: str,
        sub_device: str,
        sw_version: str,
        hw_info: HardwareInfo,
        topics: TopicContext,
    ):
        super().__init__(
            name_prefix=name_prefix,
            room=room,
            sub_device=sub_device,
            sw_version=sw_version,
            hw_info=hw_info,
            topics=topics,
        )
