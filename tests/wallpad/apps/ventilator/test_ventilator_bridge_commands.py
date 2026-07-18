from unittest.mock import MagicMock


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
    ventilator_instance._publish_ha_discovery = MagicMock()

    ventilator_instance._handle_restart("wallpad/bridge/config/restart", "")

    ventilator_instance._publish_ha_discovery.assert_called_once_with()


def test_handle_remove_republishes_discovery_with_remove_flag(ventilator_instance):
    """Ventilator도 Panel과 동등하게 remove 커맨드를 지원해야 한다."""
    ventilator_instance._publish_ha_discovery = MagicMock()

    ventilator_instance._handle_remove("wallpad/bridge/config/remove", "")

    ventilator_instance._publish_ha_discovery.assert_called_once_with(remove=True)
