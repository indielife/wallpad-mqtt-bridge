from dataclasses import dataclass


@dataclass
class MqttConfig:
    ip: str
    username: str
    password: str
    anonymous: bool
