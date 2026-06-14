import json
from unittest.mock import MagicMock, patch

import pytest

from kocom.core import (
    DEVICE_ELEVATOR,
    DEVICE_GAS,
    HA_PREFIX,
    HA_SENSOR,
    HA_SWITCH,
    Kocom,
)


@pytest.fixture
def mock_config():
    """테스트용 가짜 AppConfig 설정을 생성하는 픽스처"""
    config = MagicMock()
    config.init_temp = 22
    config.scan_interval = 300
    config.packet_delay = 0.8
    config.default_speed = "medium"
    config.kocom_light_size = {"room1": 1}
    config.kocom_plug_size = {"room1": 1}
    config.sw_version = "RS485 Compilation 0.1.0"
    config.kocom_room = {"00": "room1"}
    config.kocom_room_thermostat = {"00": "room1"}
    config.kocom_room_rev = {"room1": "00", "wallpad": "00"}
    config.kocom_room_thermostat_rev = {"room1": "00"}
    return config


@pytest.fixture
def kocom_factory(mock_config):
    """
    Kocom 인스턴스와 mock_mqtt_instance를 생성해주는 팩토리 픽스처.
    활성화할 디바이스 이름을 전달받아 해당 디바이스만 True로 설정합니다.
    """
    with (
        patch("kocom.core.Kocom.connect_mqtt") as mock_connect_mqtt,
        patch("kocom.core.threading.Thread"),
        patch("kocom.core.Kocom.get_serial"),
        patch("kocom.core.Kocom.scan_list"),
    ):
        mock_mqtt_instance = MagicMock()
        mock_connect_mqtt.return_value = mock_mqtt_instance

        def _create(active_device: str):
            mock_client = MagicMock()
            mock_client._wp_light = active_device == "light"
            mock_client._wp_fan = active_device == "fan"
            mock_client._wp_plug = active_device == "plug"
            mock_client._wp_gas = active_device == "gas"
            mock_client._wp_elevator = active_device == "elevator"
            mock_client._wp_thermostat = active_device == "thermostat"
            mock_client._mqtt = {
                "server": "test",
                "username": "",
                "password": "",
                "anonymous": "True",
            }
            mock_client._type = "serial"
            mock_client._connect = {"test_device": MagicMock()}

            wallpad = Kocom(
                mock_config, mock_client, name="test_name", device="test_device", packet_len=10
            )

            return wallpad, mock_mqtt_instance

        yield _create


@pytest.mark.parametrize(
    "active_device, expected_topics",
    [
        (
            "elevator",
            [
                f"{HA_PREFIX}/{HA_SWITCH}/wallpad_{DEVICE_ELEVATOR}/config",
            ],
        ),
        (
            "gas",
            [
                f"{HA_PREFIX}/{HA_SWITCH}/wallpad_{DEVICE_GAS}/config",
                f"{HA_PREFIX}/{HA_SENSOR}/wallpad_{DEVICE_GAS}/config",
            ],
        ),
        (
            "fan",
            [
                "homeassistant/fan/wallpad_fan/config",
            ],
        ),
        (
            "light",
            [
                "homeassistant/light/room1_light0/config",
                "homeassistant/light/room1_light1/config",
            ],
        ),
        (
            "plug",
            [
                "homeassistant/switch/room1_plug0/config",
                "homeassistant/switch/room1_plug1/config",
            ],
        ),
        (
            "thermostat",
            [
                "homeassistant/climate/room1/config",
            ],
        ),
    ],
)
@pytest.mark.parametrize(
    "initial, remove",
    [
        (False, False),  # 기본 등록 검증
        (False, True),  # 삭제 검증
        (True, False),  # 초기 구동 검증 (Subscribe 추가)
    ],
)
def test_homeassistant_device_discovery(
    snapshot, active_device, expected_topics, initial, remove, kocom_factory
):
    # 1. 의존성 팩토리로 Kocom 인스턴스 생성
    wallpad, mock_mqtt_instance = kocom_factory(active_device)

    # 2. 테스트할 메서드 실행
    wallpad.homeassistant_device_discovery(initial=initial, remove=remove)

    # 3. Publish 검증
    publish_calls = mock_mqtt_instance.publish.call_args_list
    assert len(publish_calls) > 0

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
        domain = topic.split("/")[1]
        entity_id = topic.split("/")[2]
        snapshot_name = f"{active_device}_publish_payload_{domain}_{entity_id}"

        if remove:
            assert payload == ""
        else:
            payload_dict = json.loads(payload)
            assert payload_dict == snapshot(name=snapshot_name)

    # 4. Subscribe 검증
    if initial:
        subscribe_calls = mock_mqtt_instance.subscribe.call_args_list
        assert len(subscribe_calls) > 0

        subscribe_list = subscribe_calls[0][0][0]
        assert subscribe_list == snapshot(name=f"{active_device}_subscribe_topics")
    else:
        mock_mqtt_instance.subscribe.assert_not_called()
