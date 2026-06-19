import asyncio
import logging
import logging.handlers
import os
import os.path
import sys
import time

from wallpad.config import AppConfig
from wallpad.grex import Grex
from wallpad.kocom import Kocom
from wallpad.mqtt import MqttClient
from wallpad.transport import RS485, BaseTransport
from wallpad.transport import create as create_transport
from wallpad.version import SW_VERSION

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


def _run_wallpad_serial(config: AppConfig, transport: BaseTransport, mqtt_client: MqttClient):
    if transport:
        try:
            Kocom(config, transport, config.wallpad_manufacturer, 42, mqtt_client)
        except Exception as e:
            logger.error("Failed to initialize Wallpad %s: %r", config.wallpad_manufacturer, e)


def _run_wallpad_socket(
    config: AppConfig, transport: BaseTransport, mqtt_client: MqttClient
) -> bool:
    name = config.wallpad_manufacturer

    if transport:
        logger.info("Initializing Wallpad (Socket) %s", name)
        try:
            kocom = Kocom(config, transport, name, 42, mqtt_client)
            if kocom.connection_lost():
                logger.error("Wallpad socket connection lost. Reconnecting in 1 minute...")
                time.sleep(60)
                return False
        except Exception as e:
            logger.error("Failed to initialize Wallpad socket %s: %r", name, e)
            time.sleep(60)
            return False
    return True


def run_wallpad(config: AppConfig, rs485: RS485, mqtt_client: MqttClient) -> bool:
    """Wallpad 연결 및 Kocom 초기화를 수행합니다. 소켓 모드 실패 시 False를 반환합니다."""
    if not config.wallpad_enabled:
        return True

    # 연결 시도
    if not rs485.connect_wallpad():
        logger.error("Failed to connect to Wallpad. Retrying in 1 minute...")
        time.sleep(60)
        return False

    logger.info("Initializing Wallpad %s", config.wallpad_manufacturer)

    comm_type = config.comm_type
    transport = rs485.adapters.get("wallpad")

    if comm_type == "serial":
        _run_wallpad_serial(config, transport, mqtt_client)
        return True
    elif comm_type == "socket":
        return _run_wallpad_socket(config, transport, mqtt_client)

    return True


def run_ventilator(config: AppConfig, rs485: RS485, mqtt_client: MqttClient) -> bool:
    """Ventilator 연결 및 Grex 초기화를 수행합니다."""
    if not config.ventilator_enabled:
        return True

    # 연결 시도
    if not rs485.connect_ventilator():
        logger.error("Failed to connect to Ventilator.")
        return False

    conn_type = config.ventilator_connection_type
    unit_transport = None
    ctrl_transport = None
    if conn_type == "serial":
        unit_transport = rs485.adapters.get("ventilator_unit")
        ctrl_transport = rs485.adapters.get("ventilator_ctrl")
    elif conn_type == "socket":
        logger.warning(
            "Ventilator socket mode is configured, but "
            "Grex implementation might require serial adapters."
        )
        return True

    if unit_transport and ctrl_transport:
        try:
            logger.info("Initializing Grex (Serial)")
            Grex(config, ctrl_transport, unit_transport, mqtt_client)
            return True
        except Exception as e:
            logger.error("Failed to initialize Grex: %r", e)
    else:
        logger.error("Grex adapters are not open or not available")
        return False

    return True


async def main():
    config = AppConfig()
    config.load()

    # 로그 설정
    root_dir = os.path.abspath(os.getcwd())
    log_path = os.path.join(root_dir, "log", "kocom.log")

    setup_logging(log_path, config.log_level)

    logger.info("========================================================")
    logger.info("    KOCOM Wallpad RS485 Controller Add-on  %s", SW_VERSION)
    logger.info("========================================================")

    # MqttClient 단일 인스턴스 생성 및 시작
    mqtt_client = MqttClient(config.mqtt_config)
    mqtt_client.connect()

    connection_flag = False
    while not connection_flag:
        rs485 = RS485(config)

        # 1. Wallpad 실행
        wallpad_ok = run_wallpad(config, rs485, mqtt_client)

        # 2. Ventilator 실행
        ventilator_ok = run_ventilator(config, rs485, mqtt_client)

        # 소켓 모드가 활성화되어 있고 연결에 실패한 경우 재시도 루프를 계속 돕니다.
        # 시리얼 모드만 동작할 때는 한 번 실행 후 루프를 빠져나옵니다.
        is_socket_mode = (config.wallpad_enabled and config.comm_type == "socket") or (
            config.ventilator_enabled and config.ventilator_connection_type == "socket"
        )

        if is_socket_mode and (not wallpad_ok or not ventilator_ok):
            connection_flag = False
        else:
            connection_flag = True


if __name__ == "__main__":
    asyncio.run(main())
