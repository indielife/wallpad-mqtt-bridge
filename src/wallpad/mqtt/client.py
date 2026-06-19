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
        self._message_callbacks = []
        self._subscribe_callbacks = []
        self._connected = False

    def connect(self) -> None:
        """MQTT 브로커에 TCP 연결을 수립하고 백그라운드 루프를 기동합니다."""
        if not self.config.host:
            logger.error("Host address is missing.")
            return

        if not self.config.username or not self.config.password:
            logger.error(
                "Authentication credentials are missing for server: %s",
                self.config.host,
            )
            return
        self.client.username_pw_set(username=self.config.username, password=self.config.password)
        logger.debug(
            "Authenticated connection to server: %s with user: %s",
            self.config.host,
            self.config.username,
        )

        try:
            self.client.connect(self.config.host, 1883, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error("Failed to connect to broker: %r", e)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected successfully")
            self._connected = True
        else:
            logger.error("Connection failed with error code: %s", rc)

        for cb in self._connect_callbacks:
            try:
                cb(client, userdata, flags, rc)
            except Exception as e:
                logger.error("Error in connect callback: %r", e)

    def _on_message(self, client, userdata, msg):
        for cb in self._message_callbacks:
            try:
                cb(client, userdata, msg)
            except Exception as e:
                logger.error("Error in message callback: %r", e)

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        logger.debug("Subscribed to topic. mid: %s, qos: %s", mid, granted_qos)
        for cb in self._subscribe_callbacks:
            try:
                cb(client, userdata, mid, granted_qos)
            except Exception as e:
                logger.error("Error in subscribe callback: %r", e)

    def register_connect_callback(self, callback) -> None:
        """MQTT 브로커에 정상 연결(또는 재연결)되었을 때 호출될 콜백을 등록합니다."""
        self._connect_callbacks.append(callback)

    def register_message_callback(self, callback) -> None:
        """메시지가 수신되었을 때 호출될 콜백을 등록합니다."""
        self._message_callbacks.append(callback)

    def register_subscribe_callback(self, callback) -> None:
        """토픽 구독이 완료되었을 때 호출될 콜백을 등록합니다."""
        self._subscribe_callbacks.append(callback)

    def publish(self, topic: str, payload: str, retain: bool = True) -> None:
        """MQTT 브로커로 메시지를 발행(Publish)합니다."""
        self.client.publish(topic, payload, retain=retain)

    def publish_json(self, topic: str, payload_data, retain: bool = True) -> None:
        """JSON 데이터를 직렬화하여 MQTT 브로커로 발행(Publish)합니다. (ensure_ascii=False 적용)"""
        import json

        payload = json.dumps(payload_data, ensure_ascii=False)
        self.publish(topic, payload, retain=retain)

    def subscribe(self, topic, qos=0) -> None:
        """MQTT 브로커로부터 특정 토픽 또는 토픽 리스트를 구독(Subscribe)합니다.

        topic: 단일 토픽 문자열(str) 또는 (topic, qos) 튜플의 리스트
        """
        self.client.subscribe(topic, qos)
