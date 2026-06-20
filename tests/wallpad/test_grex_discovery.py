import json
from unittest.mock import MagicMock, patch

import pytest

from wallpad.grex.grex import (
    DEVICE_FAN,
    HA_FAN,
    HA_PREFIX,
    HA_SENSOR,
    Grex,
)


@pytest.fixture
def grex_factory():
    """
    Grex 인스턴스와 mock_mqtt_instance를 생성해주는 팩토리 픽스처.
    """
    with patch("wallpad.grex.grex.threading.Thread"):
        mock_mqtt_instance = MagicMock()
        mock_mqtt_client = MagicMock()
        mock_mqtt_client.client = mock_mqtt_instance
        mock_mqtt_client.publish.side_effect = mock_mqtt_instance.publish
        mock_mqtt_client.publish_json.side_effect = lambda topic, payload, retain=True: (
            mock_mqtt_instance.publish(
                topic, json.dumps(payload, ensure_ascii=False), retain=retain
            )
        )
        mock_mqtt_client.subscribe.side_effect = mock_mqtt_instance.subscribe

        def _create():
            mock_config = MagicMock()
            mock_config.sw_version = "RS485 Compilation 0.1.0"
            mock_config.ventilator_default_speed = "low"
            mock_client = MagicMock()
            mock_client._mqtt = {
                "server": "test",
                "username": "",
                "password": "",
            }

            mock_cont_adapter = MagicMock()
            mock_vent_adapter = MagicMock()

            grex = Grex(
                mock_config,
                mock_mqtt_client,
                mock_cont_adapter,
                mock_vent_adapter,
            )
            return grex, mock_mqtt_instance

        yield _create


@pytest.mark.parametrize(
    "initial",
    [
        False,  # 기본 등록 검증
        True,  # 초기 구동 검증 (Subscribe 추가)
    ],
)
def test_grex_publish_ha_discovery(snapshot, initial, grex_factory):
    # 1. 의존성 팩토리로 Grex 인스턴스 생성
    grex, mock_mqtt_instance = grex_factory()

    # 2. 테스트할 메서드 실행
    grex.publish_ha_discovery(initial=initial)

    # 3. Publish 검증
    publish_calls = mock_mqtt_instance.publish.call_args_list
    assert len(publish_calls) > 0

    expected_topics = [
        f"{HA_PREFIX}/{HA_FAN}/grex_{DEVICE_FAN}/config",
        f"{HA_PREFIX}/{HA_SENSOR}/grex_{DEVICE_FAN}_mode/config",
        f"{HA_PREFIX}/{HA_SENSOR}/grex_{DEVICE_FAN}_speed/config",
    ]

    # 발행된 모든 토픽과 페이로드를 딕셔너리로 수집
    published_data = {}
    for call in publish_calls:
        args, _ = call
        topic = args[0]
        payload = args[1]
        published_data[topic] = payload

    # 예상한 토픽들이 정상적으로 발행되었고, 페이로드도 올바른지 검증
    for topic in expected_topics:
        assert topic in published_data, f"{topic} 토픽으로 발행되지 않았습니다."

        payload = published_data[topic]
        topic_suffix = topic.split("/")[-2]
        snapshot_name = f"grex_publish_payload_{topic_suffix}"

        payload_dict = json.loads(payload)
        assert payload_dict == snapshot(name=snapshot_name)

    # 4. Subscribe 검증
    if initial:
        subscribe_calls = mock_mqtt_instance.subscribe.call_args_list
        assert len(subscribe_calls) > 0

        subscribe_list = subscribe_calls[0][0][0]
        assert subscribe_list == snapshot(name="grex_subscribe_topics")
    else:
        mock_mqtt_instance.subscribe.assert_not_called()
