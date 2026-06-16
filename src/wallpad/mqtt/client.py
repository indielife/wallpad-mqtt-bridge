import logging

import paho.mqtt.client as mqtt

from wallpad.mqtt.config import MqttConfig

logger = logging.getLogger(__name__)


class MqttClient:
    """MQTT 브로커와의 TCP 연결 및 메시지 라우팅을 전담하는 공통 클라이언트 래퍼 클래스입니다."""

    def __init__(self, config: MqttConfig):
        self.config = config
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe
        self._connect_callbacks = []
        self._connected = False

    def connect(self) -> bool:
        """MQTT 브로커에 TCP 연결을 수립하고 백그라운드 루프를 기동합니다."""
        if not self.config.anonymous:
            if not self.config.ip or not self.config.username or not self.config.password:
                logger.error(
                    "MQTT 설정을 확인하세요. IP[%s] ID[%s] PW[%s]",
                    self.config.ip,
                    self.config.username,
                    self.config.password,
                )
                return False
            self.client.username_pw_set(
                username=self.config.username, password=self.config.password
            )
            logger.debug(
                "MQTT STATUS. IP[%s] ID[%s] PW[%s]",
                self.config.ip,
                self.config.username,
                self.config.password,
            )
        else:
            logger.debug("MQTT STATUS. IP[%s] (Anonymous)", self.config.ip)

        try:
            self.client.connect(self.config.ip, 1883, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error("Failed to connect to MQTT broker: %r", e)
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("[MQTT] Connected successfully")
            self._connected = True
            for cb in self._connect_callbacks:
                try:
                    cb()
                except Exception as e:
                    logger.error("Failed to run MQTT connect callback: %r", e)
        else:
            logger.error("[MQTT] Connection failed with code: %s", rc)

    def _on_message(self, client, userdata, msg):
        pass

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        logger.debug("[MQTT] Subscribed to topic. mid: %s, qos: %s", mid, granted_qos)

    def register_connect_callback(self, callback) -> None:
        """MQTT 브로커에 정상 연결(또는 재연결)되었을 때 호출될 콜백을 등록합니다."""
        self._connect_callbacks.append(callback)
        if self._connected:
            try:
                callback()
            except Exception as e:
                logger.error("Failed to run MQTT connect callback on registration: %r", e)

    def register_message_callback(self, topic: str, callback) -> None:
        """특정 토픽(와일드카드 지원)으로 메시지가 수신되었을 때 호출될 콜백을 등록합니다."""
        pass

    def publish(self, topic: str, payload: str, retain: bool = True) -> None:
        """MQTT 브로커로 메시지를 발행(Publish)합니다."""
        pass
