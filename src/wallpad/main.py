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


if __name__ == "__main__":
    config = AppConfig()
    config.load()

    # 로그 설정
    root_dir = os.path.abspath(os.getcwd())
    log_path = os.path.join(root_dir, "log", "kocom.log")

    setup_logging(log_path, config.log_level)

    grex_ventilator = False
    grex_controller = False
    connection_flag = False
    while not connection_flag:
        rs485 = RS485(config)
        connection_flag = True
        if rs485._type == "serial":
            for device in rs485._device:
                if rs485._connect[device].isOpen():
                    name = rs485._device[device]
                    try:
                        logger.info("[CONFIG] %s 초기화", name)
                        if name == "kocom":
                            kocom = Kocom(config, rs485, name, device, 42)
                        elif name == "grex_ventilator":
                            grex_ventilator = {
                                "serial": rs485._connect[device],
                                "name": name,
                                "length": 12,
                            }
                        elif name == "grex_controller":
                            grex_controller = {
                                "serial": rs485._connect[device],
                                "name": name,
                                "length": 11,
                            }
                    except Exception as e:
                        logger.info("[CONFIG] %s 초기화 실패: %r", name, e)
        elif rs485._type == "socket":
            name = rs485._device
            if name == "kocom":
                kocom = Kocom(config, rs485, name, name, 42)
                if not kocom.connection_lost():
                    logger.info("[ERROR] 서버 연결이 끊어져 1분 후 재접속을 시도합니다.")
                    time.sleep(60)
                    connection_flag = False

        if grex_ventilator is not False and grex_controller is not False:
            _grex = Grex(config, rs485, grex_controller, grex_ventilator)
