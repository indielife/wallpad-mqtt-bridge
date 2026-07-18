import asyncio
import logging
from collections.abc import Callable

from wallpad.devices.base import BaseDevice
from wallpad.mqtt import TOPIC_BRIDGE_REMOVE, TOPIC_BRIDGE_RESTART, MqttClient

logger = logging.getLogger(__name__)


class HaDiscoveryCoordinator:
    """HA MQTT Discovery 발행과 restart/remove 기동 핸들러를 소유하는 공용 컴포넌트.

    on_connect → discovery 발행 → restart/remove 흐름을 담당한다. 발행 후
    echo 기반 준비 핸드셰이크(ha_ready)가 필요한 쪽은
    HandshakeHaDiscoveryCoordinator를 쓴다.
    """

    def __init__(self, mqtt_client: MqttClient, devices: list[BaseDevice]):
        self.mqtt_client = mqtt_client
        self.devices = devices

    def register_routes(self) -> None:
        """restart/remove 커맨드 토픽을 등록한다. 발행 대상 토픽 등록은 호출자 몫이다."""
        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_RESTART, self._handle_restart)
        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_REMOVE, self._handle_remove)

    def on_connect(self, *_) -> None:
        self.publish()

    def publish(self, remove: bool = False) -> None:
        self._publish(self._discovery_messages(remove))

    def _discovery_messages(self, remove: bool) -> list[tuple[str, str]]:
        """활성 기기들의 (topic, payload) discovery 메시지를 발행 순서대로 모은다."""
        return [
            (topic, payload)
            for device in self.devices
            for topic, payload in device.get_discovery_payloads(remove=remove)
        ]

    def _publish(self, messages: list[tuple[str, str]]) -> None:
        for topic, payload in messages:
            self.mqtt_client.publish(topic, payload, retain=True)

    def _handle_restart(self, topic: str, payload: str) -> None:
        self.publish()
        logger.info("[From HA]HomeAssistant Restart")

    def _handle_remove(self, topic: str, payload: str) -> None:
        self.publish(remove=True)
        logger.info("[From HA]HomeAssistant Remove")


class HandshakeHaDiscoveryCoordinator(HaDiscoveryCoordinator):
    """발행 후 echo로 준비 완료를 확인하는 핸드셰이크를 추가로 관리한다.

    발행한 discovery 토픽 중 마지막 토픽을 expected_echo_topic으로 기억해두고,
    브로커가 retained 메시지로 그 토픽을 되돌려주면 ha_ready를 set한다.
    """

    def __init__(
        self,
        mqtt_client: MqttClient,
        devices: list[BaseDevice],
        loop_provider: Callable[[], asyncio.AbstractEventLoop | None],
    ):
        super().__init__(mqtt_client, devices)
        self._loop_provider = loop_provider
        self.expected_echo_topic: str | None = None
        self.ha_ready = asyncio.Event()

    def publish(self, remove: bool = False) -> None:
        self.ha_ready.clear()
        messages = self._discovery_messages(remove)
        # 에코백이 발행 도중/직후에 도착해도 매칭을 놓치지 않도록, 실제 발행에
        # 앞서 기대 토픽(마지막 discovery 토픽)을 먼저 확정한다.
        self.expected_echo_topic = messages[-1][0] if messages else None
        self._publish(messages)

    def handle_echo(self, topic: str, payload: str) -> None:
        logger.info("Message: %s = %s", topic, payload)
        loop = self._loop_provider()
        if self.expected_echo_topic is not None and self.expected_echo_topic == topic and loop:
            loop.call_soon_threadsafe(self.ha_ready.set)
