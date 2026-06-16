import json
from unittest.mock import mock_open, patch

from wallpad.config import AppConfig

SAMPLE_OPTIONS_JSON = {
    "RS485": {"type": "Serial"},
    "Socket": {"server": "192.168.1.100", "port": 8899},
    "SocketDevice": {"device": "kocom"},
    "Serial": {"port1": "/dev/ttyUSB0"},
    "SerialDevice": {"port1": "kocom"},
    "MQTT": {
        "anonymous": False,
        "server": "192.168.1.200",
        "username": "test_user",
        "password": "test_password",
    },
    "Wallpad": {
        "light": True,
        "plug": False,
        "thermostat": True,
        "fan": False,
        "gas": True,
        "elevator": False,
    },
    "Advanced": {
        "INIT_TEMP": 24,
        "SCAN_INTERVAL": 500,
        "PACKET_DELAY": 1.5,
        "DEFAULT_SPEED": "high",
        "LOGLEVEL": "debug",
    },
    "KOCOM_LIGHT_SIZE": [{"name": "livingroom", "number": 3}, {"name": "bedroom", "number": 2}],
    "KOCOM_PLUG_SIZE": [{"name": "livingroom", "number": 2}],
    "KOCOM_ROOM": ["livingroom", "bedroom"],
    "KOCOM_ROOM_THERMOSTAT": ["livingroom"],
    "Ventilator": {
        "manufacturer": "Grex",
        "connection_type": "Serial",
        "Serial": {"ventilator_port": "/dev/ttyUSB1", "controller_port": "/dev/ttyUSB2"},
        "Socket": {"ip": "192.168.1.101", "port": 8899},
        "default_speed": "low",
    },
}


@patch("wallpad.config.os.path.isfile", return_value=True)
def test_app_config_load(mock_isfile):
    """AppConfig가 options.json을 읽고 각 변수에 올바르게 매핑하는지 검증합니다."""
    mock_file = mock_open(read_data=json.dumps(SAMPLE_OPTIONS_JSON))
    with patch("builtins.open", mock_file):
        config = AppConfig(options_path="/fake/path.json")
        config.load()

        # 1. Advanced 설정 검증
        assert config.init_temp == 24
        assert config.scan_interval == 500
        assert config.packey_delay == 1.5
        assert config.kocom_default_speed == "high"
        assert config.log_level == "debug"

        # 2. 딕셔너리 리스트 (방, 조명, 플러그) 검증
        assert config.kocom_light_size == {"livingroom": 3, "bedroom": 2}
        assert config.kocom_plug_size == {"livingroom": 2}
        assert config.kocom_room == {"00": "livingroom", "01": "bedroom"}
        assert config.kocom_room_thermostat == {"00": "livingroom"}

        # 3. 통신 타입 및 소켓 설정 검증
        assert config.comm_type == "serial"
        assert config.socket_server == "192.168.1.100"
        assert config.socket_port == 8899
        assert config.socket_device == "kocom"

        # 4. 시리얼 포트 설정 검증 (빈 문자열 무시, 포트 번호 키 추출)
        assert config.port_url == {1: "/dev/ttyUSB0"}
        assert config.device_list == {1: "kocom"}

        # 5. MQTT 및 Wallpad 설정 (Boolean 타입 정상 파싱) 검증
        assert config.mqtt_config.ip == "192.168.1.200"
        assert config.mqtt_config.anonymous is False
        assert config.wp_list["light"] is True
        assert config.wp_list["plug"] is False
        assert config.wp_list["gas"] is True
        assert config.wp_list["fan"] is False

        # 6. 개별 디바이스 헬퍼 프로퍼티 검증
        assert config.wp_light is True
        assert config.wp_plug is False
        assert config.wp_gas is True
        assert config.wp_fan is False
        assert config.wp_thermostat is True
        assert config.wp_elevator is False

        # 7. 신규 전열교환기(Ventilator) 설정 파싱 검증
        assert config.ventilator == "Grex"
        assert config.ventilator_manufacturer == "Grex"
        assert config.ventilator_connection_type == "serial"
        assert config.ventilator_unit_port == "/dev/ttyUSB1"
        assert config.ventilator_ctrl_port == "/dev/ttyUSB2"
        assert config.ventilator_socket_ip == "192.168.1.101"
        assert config.ventilator_socket_port == 8899
        assert config.ventilator_default_speed == "low"


@patch("wallpad.config.os.path.isfile", return_value=False)
def test_app_config_defaults(mock_isfile):
    """options.json 파일이 없을 때 기본 방 설정 및 역방향 맵핑 프로퍼티가 올바르게 로드되는지 검증합니다."""
    config = AppConfig(options_path="/fake/nonexistent.json")
    config.load()

    # 기본 디바이스 활성화 상태는 False인지 검증
    assert config.wp_light is False
    assert config.wp_fan is False
    assert config.wp_thermostat is False
    assert config.wp_plug is False
    assert config.wp_gas is False
    assert config.wp_elevator is False
    assert config.ventilator == "None"
    assert config.kocom_default_speed == "low"
    assert config.ventilator_default_speed == "low"

    # 1. 기본 방 정보 검증
    assert config.kocom_room == {
        "00": "livingroom",
        "01": "bedroom",
        "02": "room2",
        "03": "room1",
        "04": "kitchen",
    }
    assert config.kocom_room_thermostat == {
        "00": "livingroom",
        "01": "bedroom",
        "02": "room1",
        "03": "room2",
    }

    # 2. 기본 역방향 맵핑 검증
    assert config.kocom_room_rev == {
        "livingroom": "00",
        "bedroom": "01",
        "room2": "02",
        "room1": "03",
        "kitchen": "04",
        "wallpad": "00",
    }
    assert config.kocom_room_thermostat_rev == {
        "livingroom": "00",
        "bedroom": "01",
        "room1": "02",
        "room2": "03",
    }

    # 3. 기본 기기 개수 검증
    assert config.kocom_light_size == {
        "livingroom": 3,
        "bedroom": 2,
        "room1": 2,
        "room2": 2,
        "kitchen": 3,
    }
    assert config.kocom_plug_size == {
        "livingroom": 2,
        "bedroom": 2,
        "room1": 2,
        "room2": 2,
        "kitchen": 2,
    }
