from dataclasses import dataclass


@dataclass
class MqttConfig:
    host: str
    username: str
    password: str
