from dataclasses import dataclass, field

from wallpad.mqtt import (
    HA_CLIMATE,
    HA_FAN,
    HA_LIGHT,
    HA_PREFIX,
    HA_SENSOR,
    HA_SWITCH,
)


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


class TopicBuilder:
    @staticmethod
    def for_light(room: str, sub_device: str) -> TopicContext:
        config_topic = f"{HA_PREFIX}/{HA_LIGHT}/{room}_{sub_device}/config"
        command_topic = f"{HA_PREFIX}/{HA_LIGHT}/{room}_{sub_device}/set"
        state_topic = f"{HA_PREFIX}/{HA_LIGHT}/{room}/state"

        return TopicContext(
            config_topics=[config_topic],
            command_topics=[command_topic],
            config_topic=config_topic,
            command_topic=command_topic,
            state_topic=state_topic,
        )

    @staticmethod
    def for_plug(room: str, sub_device: str) -> TopicContext:
        config_topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}_{sub_device}/config"
        command_topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}_{sub_device}/set"
        state_topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}/state"

        return TopicContext(
            config_topics=[config_topic],
            command_topics=[command_topic],
            config_topic=config_topic,
            command_topic=command_topic,
            state_topic=state_topic,
        )

    @staticmethod
    def for_thermostat(room: str) -> TopicContext:
        config_topic = f"{HA_PREFIX}/{HA_CLIMATE}/{room}/config"
        mode_command_topic = f"{HA_PREFIX}/{HA_CLIMATE}/{room}/mode"
        mode_state_topic = f"{HA_PREFIX}/{HA_CLIMATE}/{room}/state"
        temperature_command_topic = f"{HA_PREFIX}/{HA_CLIMATE}/{room}/target_temp"
        temperature_state_topic = f"{HA_PREFIX}/{HA_CLIMATE}/{room}/state"
        current_temperature_topic = f"{HA_PREFIX}/{HA_CLIMATE}/{room}/state"
        state_topic = f"{HA_PREFIX}/{HA_CLIMATE}/{room}/state"

        return TopicContext(
            config_topics=[config_topic],
            command_topics=[mode_command_topic, temperature_command_topic],
            config_topic=config_topic,
            state_topic=state_topic,
            mode_command_topic=mode_command_topic,
            mode_state_topic=mode_state_topic,
            temperature_command_topic=temperature_command_topic,
            temperature_state_topic=temperature_state_topic,
            current_temperature_topic=current_temperature_topic,
        )

    @staticmethod
    def for_fan(room: str, sub_device: str) -> TopicContext:
        config_topic = f"{HA_PREFIX}/{HA_FAN}/{room}_{sub_device}/config"
        command_topic = f"{HA_PREFIX}/{HA_FAN}/{room}/mode"
        mode_command_topic = f"{HA_PREFIX}/{HA_FAN}/{room}/mode"
        mode_state_topic = f"{HA_PREFIX}/{HA_FAN}/{room}/state"
        speed_command_topic = f"{HA_PREFIX}/{HA_FAN}/{room}/speed"
        speed_state_topic = f"{HA_PREFIX}/{HA_FAN}/{room}/state"
        state_topic = f"{HA_PREFIX}/{HA_FAN}/{room}/state"

        return TopicContext(
            config_topics=[config_topic],
            command_topics=[mode_command_topic, speed_command_topic],
            config_topic=config_topic,
            command_topic=command_topic,
            state_topic=state_topic,
            mode_command_topic=mode_command_topic,
            mode_state_topic=mode_state_topic,
            speed_command_topic=speed_command_topic,
            speed_state_topic=speed_state_topic,
        )

    @staticmethod
    def for_gas(room: str, sub_device: str) -> TopicContext:
        switch_config_topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}_{sub_device}/config"
        sensor_config_topic = f"{HA_PREFIX}/{HA_SENSOR}/{room}_{sub_device}/config"
        command_topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}_{sub_device}/set"
        switch_state_topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}_{sub_device}/state"
        sensor_state_topic = f"{HA_PREFIX}/{HA_SENSOR}/{room}_{sub_device}/state"

        return TopicContext(
            config_topics=[switch_config_topic, sensor_config_topic],
            command_topics=[command_topic],
            command_topic=command_topic,
            switch_config_topic=switch_config_topic,
            sensor_config_topic=sensor_config_topic,
            switch_state_topic=switch_state_topic,
            sensor_state_topic=sensor_state_topic,
        )

    @staticmethod
    def for_elevator(room: str, sub_device: str) -> TopicContext:
        config_topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}_{sub_device}/config"
        command_topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}_{sub_device}/set"
        state_topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}/state"

        return TopicContext(
            config_topics=[config_topic],
            command_topics=[command_topic],
            config_topic=config_topic,
            command_topic=command_topic,
            state_topic=state_topic,
        )
