import logging

from wallpad.mqtt.config import MqttConfig

logger = logging.getLogger(__name__)


class MqttClient:
    """MQTT 브로커와의 TCP 연결 및 메시지 라우팅을 전담하는 공통 클라이언트 래퍼 클래스입니다."""

    def __init__(self, config: MqttConfig):
        self.config = config
        self._connected = False

    def connect(self) -> bool:
        """MQTT 브로커에 TCP 연결을 수립하고 백그라운드 루프를 기동합니다."""
        pass

    def register_connect_callback(self, callback) -> None:
        """MQTT 브로커에 정상 연결(또는 재연결)되었을 때 호출될 콜백을 등록합니다."""
        pass

    def register_message_callback(self, topic: str, callback) -> None:
        """특정 토픽(와일드카드 지원)으로 메시지가 수신되었을 때 호출될 콜백을 등록합니다."""
        pass

    def publish(self, topic: str, payload: str, retain: bool = True) -> None:
        """MQTT 브로커로 메시지를 발행(Publish)합니다."""
        pass
