from dataclasses import dataclass, field


@dataclass
class TopicContext:
    # Discovery 및 제어용 토픽 리스트 제공을 위한 속성
    config_topics: list[str] = field(default_factory=list)
    command_topics: list[str] = field(default_factory=list)

    # 개별 필드 (디바이스별 매핑)
    config_topic: str = ""
    command_topic: str = ""
    state_topic: str = ""

    # Gas (복수 Entity 대응)
    switch_config_topic: str = ""
    sensor_config_topic: str = ""
    switch_state_topic: str = ""
    sensor_state_topic: str = ""

    # Thermostat / Fan (모드/값 제어 대응)
    mode_command_topic: str = ""
    mode_state_topic: str = ""
    temperature_command_topic: str = ""
    temperature_state_topic: str = ""
    current_temperature_topic: str = ""
    speed_command_topic: str = ""
    speed_state_topic: str = ""
