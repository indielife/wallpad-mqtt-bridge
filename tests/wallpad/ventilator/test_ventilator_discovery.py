import json
from unittest.mock import MagicMock

import pytest

from wallpad.mqtt import HA_FAN, HA_PREFIX, HA_SENSOR
from wallpad.protocol.grex.constants import DEVICE_FAN
from wallpad.ventilator.ventilator import Ventilator


@pytest.fixture
def ventilator_factory():
    """
    Ventilator 인스턴스와 mock_mqtt_instance를 생성해주는 팩토리 픽스처.
    """
    mock_mqtt_instance = MagicMock()
    mock_mqtt_client = MagicMock()
    mock_mqtt_client.client = mock_mqtt_instance
    mock_mqtt_client.publish.side_effect = mock_mqtt_instance.publish
    mock_mqtt_client.publish_json.side_effect = lambda topic, payload, retain=True: (
        mock_mqtt_instance.publish(topic, json.dumps(payload, ensure_ascii=False), retain=retain)
    )

    def _create():
        mock_config = MagicMock()
        mock_config.sw_version = "RS485 Compilation 0.1.0"
        mock_config.ventilator_default_speed = "low"

        ventilator = Ventilator(
            mock_config,
            mock_mqtt_client,
            MagicMock(),
            MagicMock(),
        )
        return ventilator, mock_mqtt_instance

    yield _create


def test_ventilator_publish_ha_discovery(snapshot, ventilator_factory):
    ventilator, mock_mqtt_instance = ventilator_factory()

    ventilator._publish_ha_discovery()

    publish_calls = mock_mqtt_instance.publish.call_args_list
    assert len(publish_calls) > 0

    expected_topics = [
        f"{HA_PREFIX}/{HA_FAN}/grex_{DEVICE_FAN}/config",
        f"{HA_PREFIX}/{HA_SENSOR}/grex_{DEVICE_FAN}_mode/config",
        f"{HA_PREFIX}/{HA_SENSOR}/grex_{DEVICE_FAN}_speed/config",
    ]

    published_data = {}
    for call in publish_calls:
        args, _ = call
        topic = args[0]
        payload = args[1]
        published_data[topic] = payload

    for topic in expected_topics:
        assert topic in published_data, f"{topic} 토픽으로 발행되지 않았습니다."

        payload = published_data[topic]
        topic_suffix = topic.split("/")[-2]
        snapshot_name = f"grex_publish_payload_{topic_suffix}"

        payload_dict = json.loads(payload)
        assert payload_dict == snapshot(name=snapshot_name)

    mock_mqtt_instance.subscribe.assert_not_called()


def test_ventilator_register_topic_routes(snapshot, ventilator_factory):
    """Ventilator 생성 시 fan 토픽과 bridge 커맨드 토픽이 등록되는지 검증."""
    ventilator, _ = ventilator_factory()

    register_calls = ventilator.mqtt_client.register_topic_callback.call_args_list
    assert len(register_calls) > 0
    registered_topics = [call.args[0] for call in register_calls]
    assert registered_topics == snapshot(name="grex_registered_topics")
