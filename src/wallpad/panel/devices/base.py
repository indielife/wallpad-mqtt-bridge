from wallpad.devices.base import BaseDevice
from wallpad.protocol.kocom import constants as kocom_const


class PanelDevice(BaseDevice):
    """Kocom 월패드 기기들이 공유하는 식별자·메타데이터 기반 클래스입니다."""

    @property
    def device_info(self) -> dict:
        return {
            "name": f"{kocom_const.NAME_PREFIX} {self.room}",
            "identifiers": f"{kocom_const.IDENTIFIER_PREFIX}_{self.room}",
            "manufacturer": kocom_const.MANUFACTURER,
            "model": kocom_const.MODEL,
            "sw_version": self.sw_version,
        }
