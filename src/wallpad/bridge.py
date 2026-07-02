import logging

from wallpad.mqtt import TOPIC_BRIDGE_LOG_LEVEL, MqttClient

logger = logging.getLogger(__name__)

_LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARN,
}


class Bridge:
    """기기에 종속되지 않는 전역 wallpad/bridge/config/* 커맨드(예: log_level)를 처리합니다."""

    def __init__(self, mqtt_client: MqttClient):
        self.mqtt_client = mqtt_client
        self._command_registry = {
            TOPIC_BRIDGE_LOG_LEVEL: self._handle_log_level,
        }
        for topic, handler in self._command_registry.items():
            self.mqtt_client.register_topic_callback(topic, handler)

    def _handle_log_level(self, topic: str, payload: str) -> None:
        level = _LOG_LEVEL_MAP.get(payload)
        if level is None:
            logger.warning("[From HA] 알 수 없는 log_level 값: %s", payload)
            return
        logging.getLogger().setLevel(level)
        logger.info("[From HA]Set Loglevel to %s", payload)
