from unittest.mock import MagicMock

from wallpad.mqtt import TOPIC_BRIDGE_REMOVE, TOPIC_BRIDGE_RESTART


def _find_handler(mock_register_topic_callback, topic):
    """등록된 콜백 중 topic에 매핑된 핸들러를 찾는다. 어떤 객체가 소유하는지에
    의존하지 않고 실제 라우팅 결과를 검증하기 위함이다."""
    for call in mock_register_topic_callback.call_args_list:
        if call.args[0] == topic:
            return call.args[1]
    raise AssertionError(f"{topic} 토픽이 등록되지 않았습니다.")


def test_handle_fan_command_ignores_discovery_config_echo(ventilator_instance):
    """discovery config 토픽 echo는 HA 명령이 아니므로 무시되어야 한다."""
    ventilator_instance.publish_state_to_ha = MagicMock()

    ventilator_instance._handle_fan_command("homeassistant/fan/grex_fan/config", "{}")

    assert ventilator_instance.state.desired == {"mode": "off", "speed": "off"}
    ventilator_instance.publish_state_to_ha.assert_not_called()


def test_handle_fan_command_mode_on_uses_default_speed(ventilator_instance):
    """모드 on 명령 수신 시 speed가 off였다면 default_speed로 채워진다."""
    ventilator_instance._handle_fan_command("homeassistant/fan/grex/mode", "on")

    assert ventilator_instance.state.desired["mode"] == "on"
    assert ventilator_instance.state.desired["speed"] == ventilator_instance.default_speed


def test_handle_fan_command_speed_updates_state(ventilator_instance):
    ventilator_instance._handle_fan_command("homeassistant/fan/grex/speed", "high")

    assert ventilator_instance.state.desired["speed"] == "high"


def test_handle_fan_command_publishes_when_mode_and_speed_off(ventilator_instance):
    """mode/speed 둘 다 off가 되면 HA로 상태를 발행한다."""
    ventilator_instance._handle_fan_command("homeassistant/fan/grex/speed", "high")
    ventilator_instance.publish_state_to_ha = MagicMock()

    ventilator_instance._handle_fan_command("homeassistant/fan/grex/mode", "off")
    ventilator_instance.publish_state_to_ha.assert_not_called()

    ventilator_instance._handle_fan_command("homeassistant/fan/grex/speed", "off")
    ventilator_instance.publish_state_to_ha.assert_called_once()


def test_handle_restart_republishes_discovery(ventilator_instance):
    """TOPIC_BRIDGE_RESTART가 공유 ha_coordinator로 라우팅되어 재발행을 트리거하는지 검증."""
    ventilator_instance.ha_coordinator.publish = MagicMock()
    handler = _find_handler(
        ventilator_instance.mqtt_client.register_topic_callback, TOPIC_BRIDGE_RESTART
    )

    handler(TOPIC_BRIDGE_RESTART, "")

    ventilator_instance.ha_coordinator.publish.assert_called_once_with()


def test_handle_remove_republishes_discovery_with_remove_flag(ventilator_instance):
    """Ventilator도 Panel과 동등하게 remove 커맨드를 지원해야 한다."""
    ventilator_instance.ha_coordinator.publish = MagicMock()
    handler = _find_handler(
        ventilator_instance.mqtt_client.register_topic_callback, TOPIC_BRIDGE_REMOVE
    )

    handler(TOPIC_BRIDGE_REMOVE, "")

    ventilator_instance.ha_coordinator.publish.assert_called_once_with(remove=True)
