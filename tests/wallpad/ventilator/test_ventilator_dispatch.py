"""dispatch_packet 라우팅 및 handle_* 핸들러 동작 단위 테스트."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from wallpad.mqtt import HA_FAN, HA_SENSOR
from wallpad.protocol.grex.constants import (
    PREFIX_CONTROLLER_ERROR,
    PREFIX_CONTROLLER_STATUS,
    PREFIX_VENTILATOR_STATUS,
)

# d0 8a 00 00 01 00 01 01 00 00 → mode=auto(0100), speed=low(0101), checksum=8d
CTRL_STATUS_AUTO_LOW = "d08a00000100010100008d"

# d1 8b 00 00 01 01 00 00 00 00 00 → speed=low(0101), checksum=8d
VENT_STATUS_LOW = "d18b0000010100000000008d"

# d0 0a 00 00 00 00 00 00 00 00 → controller error, checksum=0a
CTRL_ERROR = "d00a000000000000000a"


# ---------------------------------------------------------------------------
# dispatch_packet 라우팅 테스트
# ---------------------------------------------------------------------------


async def test_dispatch_routes_controller_error(ventilator_instance):
    """PREFIX_CONTROLLER_ERROR 패킷 → handle_controller_error 호출."""
    ventilator_instance.handle_controller_error = AsyncMock()

    await ventilator_instance.dispatch_packet(CTRL_ERROR)

    ventilator_instance.handle_controller_error.assert_called_once()


async def test_dispatch_routes_controller_status(ventilator_instance):
    """PREFIX_CONTROLLER_STATUS 패킷 → handle_controller_status에 parsed dict 전달."""
    ventilator_instance.handle_controller_status = AsyncMock()

    await ventilator_instance.dispatch_packet(CTRL_STATUS_AUTO_LOW)

    ventilator_instance.handle_controller_status.assert_called_once_with(
        {"type": PREFIX_CONTROLLER_STATUS, "mode": "auto", "speed": "low"},
    )


async def test_dispatch_routes_ventilator_status(ventilator_instance):
    """PREFIX_VENTILATOR_STATUS 패킷 → handle_ventilator_status에 parsed dict 전달."""
    ventilator_instance.handle_ventilator_status = MagicMock()

    await ventilator_instance.dispatch_packet(VENT_STATUS_LOW)

    ventilator_instance.handle_ventilator_status.assert_called_once_with(
        {"type": PREFIX_VENTILATOR_STATUS, "speed": "low"},
    )


async def test_dispatch_unknown_packet_early_return(ventilator_instance):
    """parse_frame이 None을 반환하면 어떤 핸들러도 호출되지 않는다."""
    ventilator_instance.handle_controller_error = AsyncMock()
    ventilator_instance.handle_controller_status = AsyncMock()
    ventilator_instance.handle_ventilator_status = MagicMock()
    ventilator_instance.parser.parse_frame = MagicMock(return_value=None)

    await ventilator_instance.dispatch_packet("ffffffffffffffffffffffff")

    ventilator_instance.handle_controller_error.assert_not_called()
    ventilator_instance.handle_controller_status.assert_not_called()
    ventilator_instance.handle_ventilator_status.assert_not_called()


# ---------------------------------------------------------------------------
# handle_controller_status 핸들러 동작 테스트
# ---------------------------------------------------------------------------


@pytest.fixture
def ventilator_with_mock_publish(ventilator_instance):
    ventilator_instance.publish_state_to_ha = MagicMock()
    ventilator_instance.controller_transport.write = AsyncMock()
    ventilator_instance.ventilator_transport.write = AsyncMock()
    return ventilator_instance


async def test_handle_controller_status_state_change_updates_cont(
    ventilator_with_mock_publish,
):
    """상태 변경 시 controller_status가 갱신되고 HA에 publish된다."""
    v = ventilator_with_mock_publish
    parsed = {"type": PREFIX_CONTROLLER_STATUS, "mode": "auto", "speed": "low"}

    await v.handle_controller_status(parsed)

    assert v.state.controller_status == {"mode": "auto", "speed": "low"}
    assert v.publish_state_to_ha.call_count == 2
    calls = {c.args[0] for c in v.publish_state_to_ha.call_args_list}
    assert HA_FAN in calls
    assert HA_SENSOR in calls


async def test_handle_controller_status_no_change_skips_publish(
    ventilator_with_mock_publish,
):
    """이전 상태와 동일하면 publish가 발생하지 않는다."""
    v = ventilator_with_mock_publish
    v.state.controller_status = {"mode": "auto", "speed": "low"}
    parsed = {"type": PREFIX_CONTROLLER_STATUS, "mode": "auto", "speed": "low"}

    await v.handle_controller_status(parsed)

    v.publish_state_to_ha.assert_not_called()


# ---------------------------------------------------------------------------
# handle_ventilator_status 핸들러 동작 테스트
# ---------------------------------------------------------------------------


def test_handle_ventilator_status_speed_change_updates_cont(
    ventilator_with_mock_publish,
):
    """속도 변경 시 ventilator_status가 갱신되고 HA에 publish된다."""
    v = ventilator_with_mock_publish
    parsed = {"type": PREFIX_VENTILATOR_STATUS, "speed": "medium"}

    v.handle_ventilator_status(parsed)

    assert v.state.ventilator_status["speed"] == "medium"
    assert v.publish_state_to_ha.call_count == 2


def test_handle_ventilator_status_no_change_skips_publish(
    ventilator_with_mock_publish,
):
    """이전 속도와 동일하면 publish가 발생하지 않는다."""
    v = ventilator_with_mock_publish
    v.state.ventilator_status = {"speed": "medium"}
    parsed = {"type": PREFIX_VENTILATOR_STATUS, "speed": "medium"}

    v.handle_ventilator_status(parsed)

    v.publish_state_to_ha.assert_not_called()
