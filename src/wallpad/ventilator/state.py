from dataclasses import dataclass, field


def off_state() -> dict[str, str]:
    """mode/speed가 모두 off인 초기 상태 dict를 생성합니다."""
    return {"mode": "off", "speed": "off"}


@dataclass
class VentilatorState:
    """환기장치의 세 갈래 상태를 묶는 컨테이너입니다.

    - controller_status: RS485 컨트롤러(월패드)가 보고한 상태 (구 grex_cont)
    - ventilator_status: RS485 환기 본체가 보고한 상태 (구 vent_cont)
    - desired: HA가 요청한 상태 (구 mqtt_cont)
    """

    controller_status: dict[str, str] = field(default_factory=off_state)
    ventilator_status: dict[str, str] = field(default_factory=off_state)
    desired: dict[str, str] = field(default_factory=off_state)
