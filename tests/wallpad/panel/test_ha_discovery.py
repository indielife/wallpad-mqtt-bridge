import json
from unittest.mock import MagicMock

import pytest

from wallpad.mqtt import HA_PREFIX, HA_SENSOR, HA_SWITCH
from wallpad.panel.panel import WallpadPanel
from wallpad.protocol.kocom.constants import DEVICE_ELEVATOR, DEVICE_GAS


def _make_room(name, room_no=None, light_count=0, plug_count=0, thermo_no=None):
    r = MagicMock()
    r.name = name
    r.room_no = room_no
    r.light_count = light_count
    r.plug_count = plug_count
    r.thermo_no = thermo_no
    r.light_addr = f"{room_no:02d}" if room_no is not None else None
    r.thermo_addr = f"{thermo_no:02d}" if thermo_no is not None else None
    return r


@pytest.fixture
def mock_config():
    """테스트용 가짜 AppConfig 설정을 생성하는 픽스처"""
    config = MagicMock()
    config.sw_version = "RS485 Compilation 0.1.0"
    config.wallpad_manufacturer = "test_name"
    config.init_temp = 22
    config.kocom_default_speed = "low"
    config.kocom_room_rev = {"room1": "00", "wallpad": "00"}
    config.kocom_room_thermostat_rev = {"room1": "00"}
    config.ventilator_default_speed = "low"
    return config


@pytest.fixture
def kocom_factory(mock_config):
    """
    WallpadPanel 인스턴스와 mock_mqtt_instance를 생성해주는 팩토리 픽스처.
    활성화할 디바이스 이름을 전달받아 해당 디바이스만 설정합니다.
    """
    mock_mqtt_instance = MagicMock()
    mock_mqtt_client = MagicMock()
    mock_mqtt_client.client = mock_mqtt_instance
    mock_mqtt_client.publish.side_effect = mock_mqtt_instance.publish
    mock_mqtt_client.publish_json.side_effect = lambda topic, payload, retain=True: (
        mock_mqtt_instance.publish(topic, json.dumps(payload, ensure_ascii=False), retain=retain)
    )
    mock_mqtt_client.subscribe.side_effect = mock_mqtt_instance.subscribe

    def _create(active_device: str):
        mock_config.mqtt_config = {"server": "test", "username": "", "password": ""}

        # 집 전체 단위 기기
        mock_config.fan_enabled = active_device == "fan"
        mock_config.gas_enabled = active_device == "gas"
        mock_config.elevator_enabled = active_device == "elevator"

        # 방 기반 기기: active_device에 맞는 rooms 설정
        if active_device == "light":
            mock_config.rooms = [_make_room("room1", room_no=0, light_count=1)]
        elif active_device == "plug":
            mock_config.rooms = [_make_room("room1", room_no=0, plug_count=1)]
        elif active_device == "thermostat":
            mock_config.rooms = [_make_room("room1", thermo_no=0)]
        else:
            mock_config.rooms = []

        panel = WallpadPanel(mock_config, mock_mqtt_client, MagicMock())
        return panel, mock_mqtt_instance

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
    "remove",
    [
        False,  # 기본 등록 검증
        True,  # 삭제 검증
    ],
)
def test_publish_ha_discovery(snapshot, active_device, expected_topics, remove, kocom_factory):
    # 1. 의존성 팩토리로 WallpadPanel 인스턴스 생성
    wallpad, mock_mqtt_instance = kocom_factory(active_device)

    # 2. 테스트할 메서드 실행
    wallpad._publish_ha_discovery(remove=remove)

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

    mock_mqtt_instance.subscribe.assert_not_called()


@pytest.mark.parametrize(
    "active_device",
    ["elevator", "gas", "fan", "light", "plug", "thermostat"],
)
def test_subscribe_ha_topics(snapshot, active_device, kocom_factory):
    wallpad, mock_mqtt_instance = kocom_factory(active_device)

    wallpad._subscribe_ha_topics()

    subscribe_calls = mock_mqtt_instance.subscribe.call_args_list
    assert len(subscribe_calls) > 0
    subscribe_list = subscribe_calls[0][0][0]
    assert subscribe_list == snapshot(name=f"{active_device}_subscribe_topics")
