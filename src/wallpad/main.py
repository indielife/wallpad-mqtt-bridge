import logging
import logging.handlers
import os
import os.path
import sys
import time

from wallpad.config import AppConfig
from wallpad.grex import Grex
from wallpad.kocom import Kocom
from wallpad.rs485 import RS485

logger = logging.getLogger(__name__)


def setup_logging(path: str, level: str = "info"):
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARN,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    log_level = log_levels.get(level.lower(), logging.INFO)

    # 1. 폴더 자동 생성
    log_dir = os.path.dirname(path)
    if log_dir and not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    # 2. 파일 핸들러 설정 (기존 1MB 제한 및 10개 백업 유지)
    max_bytes = 1024 * 1024  # 1MB
    file_handler = logging.handlers.RotatingFileHandler(
        filename=path, maxBytes=max_bytes, backupCount=10, encoding="utf-8"
    )

    # 3. 콘솔 출력 핸들러 설정
    stream_handler = logging.StreamHandler()

    # 4. 루트 로거 설정을 통해 모든 하위 모듈(grex, rs485 등)에 일괄 적용
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s:%(lineno)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            file_handler,
            stream_handler,
        ],
    )


def run_serial_mode(config: AppConfig, rs485: RS485):
    grex_ventilator_adapter = None
    grex_controller_adapter = None
    for port_key, adapter in rs485.adapters.items():
        if not adapter.is_open():
            continue
        name = rs485.config.device_list.get(port_key)
        try:
            logger.info("Initializing %s", name)
            if name == "kocom":
                Kocom(config, adapter, name, 42)
            elif name == "grex_ventilator":
                grex_ventilator_adapter = adapter
            elif name == "grex_controller":
                grex_controller_adapter = adapter
        except Exception as e:
            logger.error("Failed to initialize %s: %r", name, e)

    if grex_ventilator_adapter is not None and grex_controller_adapter is not None:
        Grex(config, grex_controller_adapter, grex_ventilator_adapter)


def run_socket_mode(config: AppConfig, rs485: RS485) -> bool:
    name = rs485.config.socket_device
    adapter = rs485.adapters.get(name)
    if name == "kocom" and adapter:
        logger.info("Initializing %s", name)
        try:
            kocom = Kocom(config, adapter, name, 42)
            if not kocom.connection_lost():
                logger.error("Server connection lost. Reconnecting in 1 minute...")
                time.sleep(60)
                return False
        except Exception as e:
            logger.error("Failed to initialize %s: %r", name, e)
            time.sleep(60)
            return False
    return True


if __name__ == "__main__":
    config = AppConfig()
    config.load()

    # 로그 설정
    root_dir = os.path.abspath(os.getcwd())
    log_path = os.path.join(root_dir, "log", "kocom.log")

    setup_logging(log_path, config.log_level)

    connection_flag = False
    while not connection_flag:
        rs485 = RS485(config)
        if rs485.type == "serial":
            run_serial_mode(config, rs485)
            connection_flag = True
        elif rs485.type == "socket":
            connection_flag = run_socket_mode(config, rs485)
