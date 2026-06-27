import asyncio
import logging
import logging.handlers
import os
import os.path

from wallpad.config import AppConfig
from wallpad.mqtt import MqttClient
from wallpad.panel import Panel
from wallpad.transport import (
    create_ventilator_transports,
    create_wallpad_transport,
)
from wallpad.ventilator import Ventilator
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

    log_dir = os.path.dirname(path)
    if log_dir and not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    max_bytes = 1024 * 1024  # 1MB
    file_handler = logging.handlers.RotatingFileHandler(
        filename=path, maxBytes=max_bytes, backupCount=10, encoding="utf-8"
    )
    stream_handler = logging.StreamHandler()

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s:%(lineno)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[file_handler, stream_handler],
    )


async def run_wallpad(config: AppConfig, mqtt_client: MqttClient) -> list[asyncio.Task]:
    """Wallpad 연결 및 Kocom 초기화를 수행합니다. 실패 시 빈 리스트를 반환합니다."""
    if not config.wallpad_enabled:
        return []

    try:
        logger.info("Initializing Wallpad %s", config.wallpad_manufacturer)
        transport = create_wallpad_transport(config)
        panel = Panel(config, mqtt_client, transport)
        return await panel.start()
    except Exception as e:
        logger.error("Failed to initialize Wallpad %s: %r", config.wallpad_manufacturer, e)
        return []


async def run_ventilator(config: AppConfig, mqtt_client: MqttClient) -> list[asyncio.Task]:
    """Ventilator 연결 및 Grex 초기화를 수행합니다. 실패 시 빈 리스트를 반환합니다."""
    if not config.ventilator_enabled:
        return []

    if config.ventilator_connection_type == "socket":
        logger.warning(
            "Ventilator socket mode is configured, but "
            "Grex implementation might require serial adapters."
        )
        return []

    try:
        logger.info("Initializing Grex (Serial)")
        ctrl_transport, unit_transport = create_ventilator_transports(config)
        ventilator = Ventilator(config, mqtt_client, ctrl_transport, unit_transport)
        return await ventilator.start()
    except Exception as e:
        logger.error("Failed to initialize Grex: %r", e)
        return []


async def main():
    config = AppConfig()
    config.load()
    config.validate()

    root_dir = os.path.abspath(os.getcwd())
    log_path = os.path.join(root_dir, "log", "kocom.log")
    setup_logging(log_path, config.log_level)

    logger.info("========================================================")
    logger.info("    KOCOM Wallpad RS485 Controller Add-on  %s", SW_VERSION)
    logger.info("========================================================")

    mqtt_client = MqttClient(config.mqtt_config)

    tasks = await run_wallpad(config, mqtt_client)
    tasks += await run_ventilator(config, mqtt_client)

    mqtt_client.connect()

    if not tasks:
        logger.error("실행할 기기가 없습니다. 종료합니다.")
        return

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
