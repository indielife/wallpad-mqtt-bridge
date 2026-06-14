import json
import time
from unittest.mock import MagicMock

import pytest

from kocom.core import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    Kocom,
)
from kocom.state import KocomStateManager


@pytest.fixture
def mock_config():
    """테스트용 설정 모킹"""
    config = MagicMock()
    config.init_temp = 22
    config.scan_interval = 300
    config.packet_delay = 0.8
    config.default_speed = "medium"
    config.kocom_light_size = {"livingroom": 3}
    config.kocom_plug_size = {"livingroom": 2}
    config.sw_version = "0.1.0"
    config.kocom_room = {
        "00": "livingroom",
        "01": "bedroom",
    }
    config.kocom_room_thermostat = {
        "00": "livingroom",
        "01": "bedroom",
    }
    config.kocom_room_rev = {
        "livingroom": "00",
        "bedroom": "01",
        "wallpad": "00",
    }
    config.kocom_room_thermostat_rev = {
        "livingroom": "00",
        "bedroom": "01",
    }
    return config


@pytest.fixture
def kocom_instance(mock_config):
    """상위 흐름 테스트를 위해 최소한의 상태만 구성한 Kocom 인스턴스"""
    kocom = Kocom.__new__(Kocom)
    kocom.config = mock_config
    kocom.default_speed = "medium"
    kocom.ha_registry = False
    kocom.kocom_scan = False
    kocom._name = "kocom"
    kocom.connected = True

    # MQTT 및 시리얼 모킹
    kocom.d_mqtt = MagicMock()
    kocom.write = MagicMock()

    # wp_list 초기화 (KocomStateManager 구조)
    kocom.wp_list = KocomStateManager()
    initial_states = {
        DEVICE_LIGHT: {
            "livingroom": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "light1": {"state": "off", "set": "off", "last": "state", "count": 0},
                "light2": {"state": "off", "set": "off", "last": "state", "count": 0},
                "light3": {"state": "off", "set": "off", "last": "state", "count": 0},
            }
        },
        DEVICE_PLUG: {
            "livingroom": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "plug1": {"state": "on", "set": "on", "last": "state", "count": 0},
                "plug2": {"state": "on", "set": "on", "last": "state", "count": 0},
            }
        },
        DEVICE_THERMOSTAT: {
            "livingroom": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "mode": {"state": "off", "set": "off", "last": "state", "count": 0},
                "current_temp": {"state": 0, "set": 0, "last": "state", "count": 0},
                "target_temp": {"state": 22, "set": 22, "last": "state", "count": 0},
            }
        },
        DEVICE_FAN: {
            "wallpad": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "mode": {"state": "off", "set": "off", "last": "state", "count": 0},
                "speed": {"state": "off", "set": "off", "last": "state", "count": 0},
            }
        },
        DEVICE_GAS: {
            "wallpad": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "gas": {"state": "off", "set": "off", "last": "state", "count": 0},
            }
        },
        DEVICE_ELEVATOR: {
            "wallpad": {
                "scan": {"tick": 0.0, "count": 0, "last": 0.0},
                "elevator": {"state": "off", "set": "off", "last": "state", "count": 0},
            }
        },
    }
    for device, rooms in initial_states.items():
        kocom.wp_list[device] = rooms

    return kocom


def test_parse_message_light_plug(kocom_instance):
    """MQTT 조명 및 콘센트 제어 메시지가 들어왔을 때 wp_list 상태 변경을 검증합니다."""
    # 조명 1 켜기 명령어 처리
    topic_light = ["homeassistant", "light", "livingroom_light1", "set"]
    kocom_instance.parse_message(topic_light, "on")
    assert kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["light1"]["set"] == "on"
    assert kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["light1"]["last"] == "set"

    # 콘센트 2 끄기 명령어 처리
    topic_plug = ["homeassistant", "switch", "livingroom_plug2", "set"]
    kocom_instance.parse_message(topic_plug, "off")
    assert kocom_instance.wp_list[DEVICE_PLUG]["livingroom"]["plug2"]["set"] == "off"
    assert kocom_instance.wp_list[DEVICE_PLUG]["livingroom"]["plug2"]["last"] == "set"


def test_parse_message_gas_and_elevator(kocom_instance):
    """MQTT 가스밸브 및 엘리베이터 제어 메시지 처리 흐름을 검증합니다."""
    # 가스밸브 'on' 명령어 차단 여부 검증
    topic_gas = ["homeassistant", "switch", "wallpad_gas", "set"]
    kocom_instance.parse_message(topic_gas, "on")
    assert (
        kocom_instance.wp_list[DEVICE_GAS]["wallpad"]["gas"]["set"] == "off"
    )  # "on"은 허용되지 않음

    # 가스밸브 'off' 명령어는 허용
    kocom_instance.parse_message(topic_gas, "off")
    assert kocom_instance.wp_list[DEVICE_GAS]["wallpad"]["gas"]["set"] == "off"
    assert kocom_instance.wp_list[DEVICE_GAS]["wallpad"]["gas"]["last"] == "set"

    # 엘리베이터 'on' 명령어 처리 검증
    topic_elevator = ["homeassistant", "switch", "wallpad_elevator", "set"]
    kocom_instance.parse_message(topic_elevator, "on")
    assert kocom_instance.wp_list[DEVICE_ELEVATOR]["wallpad"]["elevator"]["set"] == "on"
    assert kocom_instance.wp_list[DEVICE_ELEVATOR]["wallpad"]["elevator"]["last"] == "set"


def test_parse_message_thermostat(kocom_instance):
    """MQTT 보일러 목표 온도 및 모드 제어 메시지가 들어왔을 때 wp_list 상태 변경을 검증합니다."""
    # 보일러 온도 25도로 변경 시 모드는 자동으로 heat으로 작동
    topic_temp = ["homeassistant", "climate", "livingroom", "target_temp"]
    kocom_instance.parse_message(topic_temp, "25.0")
    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["target_temp"]["set"] == 25
    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["mode"]["set"] == "heat"
    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["target_temp"]["last"] == "set"
    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["mode"]["last"] == "set"

    # 보일러 모드 끄기 명령어 처리
    topic_mode = ["homeassistant", "climate", "livingroom", "mode"]
    kocom_instance.parse_message(topic_mode, "off")
    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["mode"]["set"] == "off"
    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["mode"]["last"] == "set"


def test_parse_message_fan(kocom_instance):
    """MQTT 환기팬 제어 메시지가 들어왔을 때 wp_list 상태 변경을 검증합니다."""
    # 환기팬 모드 on 변경 시 기본 속도는 default_speed (medium)으로 작동
    topic_mode = ["homeassistant", "fan", "wallpad", "mode"]
    kocom_instance.parse_message(topic_mode, "on")
    assert kocom_instance.wp_list[DEVICE_FAN]["wallpad"]["mode"]["set"] == "on"
    assert kocom_instance.wp_list[DEVICE_FAN]["wallpad"]["speed"]["set"] == "medium"
    assert kocom_instance.wp_list[DEVICE_FAN]["wallpad"]["mode"]["last"] == "set"
    assert kocom_instance.wp_list[DEVICE_FAN]["wallpad"]["speed"]["last"] == "set"

    # 환기팬 스피드 high 변경
    topic_speed = ["homeassistant", "fan", "wallpad", "speed"]
    kocom_instance.parse_message(topic_speed, "high")
    assert kocom_instance.wp_list[DEVICE_FAN]["wallpad"]["speed"]["set"] == "high"
    assert kocom_instance.wp_list[DEVICE_FAN]["wallpad"]["mode"]["set"] == "on"


def test_packet_parsing_light_status(kocom_instance):
    """RS485 조명 상태 수신 패킷 파싱 시 wp_list 상태 업데이트를 검증합니다."""
    # 거실(livingroom) 조명 상태 수신 ACK 패킷 (light1 켜짐, light2 & light3 꺼짐)
    # aa55(header) 30d(type:ack) 0(order) 00(pad) 0e(light) 00(livingroom) 0100(dst:wallpad) 00(상태) ff00000000000000(value) 00(checksum) 0d0d(tail)
    packet = "aa5530d0000e00010000ff00000000000000000d0d"
    kocom_instance.packet_parsing(packet)

    assert kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["light1"]["state"] == "on"
    assert kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["light2"]["state"] == "off"
    assert kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["light3"]["state"] == "off"
    assert kocom_instance.wp_list[DEVICE_LIGHT]["livingroom"]["scan"]["tick"] > 0.0


def test_packet_parsing_thermostat_status(kocom_instance):
    """RS485 보일러 상태 수신 패킷 파싱 시 wp_list 상태 업데이트를 검증합니다."""
    # 거실(livingroom) 보일러 상태 수신 ACK 패킷 (heat모드, 목표 22도, 현재 20도)
    # aa55 30d 0 00 36(thermo) 00(livingroom) 0100(dst:wallpad) 00(상태) 1100160014000000(value) 00 0d0d
    packet = "aa5530d00036000100001100160014000000000d0d"
    kocom_instance.packet_parsing(packet)

    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["mode"]["state"] == "heat"
    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["target_temp"]["state"] == 22
    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["current_temp"]["state"] == 20
    assert kocom_instance.wp_list[DEVICE_THERMOSTAT]["livingroom"]["scan"]["tick"] > 0.0
