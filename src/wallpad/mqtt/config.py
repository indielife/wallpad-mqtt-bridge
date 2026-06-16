from dataclasses import dataclass


@dataclass
class MqttConfig:
    server: str
    username: str
    password: str
