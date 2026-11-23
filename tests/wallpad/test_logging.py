"""애드온 진단 로그의 보존·추출 경계를 검증한다."""

import logging
from pathlib import Path
from unittest.mock import patch

from wallpad.main import setup_logging


def test_addon_log_uses_existing_shared_mount(monkeypatch):
    from wallpad.main import get_log_path

    monkeypatch.setattr("wallpad.main.os.path.isdir", lambda p: p == "/share")
    assert get_log_path() == "/share/wallpad-mqtt-bridge/log/kocom.log"


def test_local_log_path_does_not_require_addon_mount(tmp_path, monkeypatch):
    from wallpad.main import get_log_path

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("wallpad.main.os.path.isdir", lambda p: False)
    assert get_log_path() == str(tmp_path / "log" / "kocom.log")


def test_unwritable_log_directory_keeps_console_logging(tmp_path, caplog):
    with (
        patch("wallpad.main.os.makedirs", side_effect=PermissionError("read only")),
        patch("wallpad.main.logging.basicConfig") as basic,
    ):
        setup_logging(str(tmp_path / "missing" / "kocom.log"))
    handlers = basic.call_args.kwargs["handlers"]
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.StreamHandler)
    assert "event=file_logging_unavailable" in caplog.text


def test_file_logging_rotates_with_bounded_retention(tmp_path):
    path = tmp_path / "logs" / "kocom.log"
    with patch("wallpad.main.logging.basicConfig") as basic:
        setup_logging(str(path), "debug")
    handlers = basic.call_args.kwargs["handlers"]
    file_handler = next(h for h in handlers if isinstance(h, logging.handlers.RotatingFileHandler))
    try:
        assert file_handler.maxBytes == 1024 * 1024
        assert file_handler.backupCount == 10
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "diagnostic", (), None)
        file_handler.handle(record)
        file_handler.doRollover()
        file_handler.handle(record)
        assert "diagnostic" in path.read_text()
        assert "diagnostic" in Path(str(path) + ".1").read_text()
    finally:
        file_handler.close()


def test_runtime_summary_omits_connection_secrets(mock_config, caplog):
    from wallpad.main import log_runtime_config

    mock_config.socket_host = "private-host"
    mock_config.mqtt_config = {"password": "private-password"}
    caplog.set_level("INFO")
    log_runtime_config(mock_config)
    assert "event=runtime_config" in caplog.text
    assert "scan_interval=" in caplog.text
    assert "private-host" not in caplog.text
    assert "private-password" not in caplog.text
