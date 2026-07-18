import logging
from unittest.mock import MagicMock

import pytest

from wallpad.bridge import Bridge
from wallpad.mqtt import TOPIC_BRIDGE_LOG_LEVEL


@pytest.fixture
def _restore_root_log_level():
    """루트 로거 레벨은 전역 상태이므로 테스트 전후로 원상 복구합니다."""
    original_level = logging.getLogger().level
    yield
    logging.getLogger().setLevel(original_level)


def test_bridge_registers_log_level_topic_callback():
    mqtt_client = MagicMock()
    bridge = Bridge(mqtt_client)

    mqtt_client.register_topic_callback.assert_called_once_with(
        TOPIC_BRIDGE_LOG_LEVEL, bridge._handle_log_level
    )


@pytest.mark.parametrize(
    ("payload", "expected_level"),
    [
        ("debug", logging.DEBUG),
        ("info", logging.INFO),
        ("warn", logging.WARN),
    ],
)
def test_log_level_command_changes_root_logger(_restore_root_log_level, payload, expected_level):
    """log_level 커맨드가 panel/ventilator 모듈 구분 없이 루트 로거에 적용되는지 검증합니다."""
    other_logger = logging.getLogger("wallpad.apps.ventilator.ventilator")

    bridge = Bridge(MagicMock())
    bridge._handle_log_level(TOPIC_BRIDGE_LOG_LEVEL, payload)

    assert other_logger.getEffectiveLevel() == expected_level


def test_log_level_command_ignores_unknown_value(_restore_root_log_level, caplog):
    """알 수 없는 log_level 값이 오면 로그레벨을 변경하지 않고 warning을 남깁니다."""
    original_level = logging.getLogger().level

    bridge = Bridge(MagicMock())
    with caplog.at_level(logging.WARNING):
        bridge._handle_log_level(TOPIC_BRIDGE_LOG_LEVEL, "trace")

    assert logging.getLogger().level == original_level
    assert "알 수 없는 log_level 값" in caplog.text
