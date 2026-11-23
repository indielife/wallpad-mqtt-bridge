import asyncio
import logging
import logging.handlers
import os
import os.path

from wallpad.apps.panel import Panel
from wallpad.apps.ventilator import Ventilator
from wallpad.bridge import Bridge
from wallpad.config import AppConfig
from wallpad.mqtt import MqttClient
from wallpad.transport import (
    create_panel_transport,
    create_ventilator_transports,
)
from wallpad.version import SW_VERSION

logger = logging.getLogger(__name__)


def get_log_path() -> str:
    if os.path.isdir("/share"):
        return "/share/wallpad-mqtt-bridge/log/kocom.log"
    return os.path.join(os.path.abspath(os.getcwd()), "log", "kocom.log")


def setup_logging(path: str, level: str = "info"):
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARN,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    log_level = log_levels.get(level.lower(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    file_error: OSError | None = None
    try:
        log_dir = os.path.dirname(path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                filename=path, maxBytes=1024 * 1024, backupCount=10, encoding="utf-8"
            )
        )
    except OSError as exc:
        file_error = exc

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s:%(lineno)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    if file_error is not None:
        logger.warning("event=file_logging_unavailable path=%s error=%r", path, file_error)
    else:
        logger.info("event=file_logging_ready path=%s max_bytes=1048576 backups=10", path)


def log_runtime_config(config: AppConfig) -> None:
    logger.info(
        "event=runtime_config version=%s transport=%s scan_interval=%s packet_delay=%s "
        "thermostat_rooms=%s",
        config.sw_version,
        config.comm_type,
        config.scan_interval,
        config.packet_delay,
        sum(room.thermo_addr is not None for room in config.rooms),
    )


async def run_panel(config: AppConfig, mqtt_client: MqttClient) -> list[asyncio.Task]:
    """Panel 연결 및 초기화를 수행합니다. 실패 시 빈 리스트를 반환합니다."""
    if not config.wallpad_enabled:
        return []

    try:
        logger.info("Initializing Wallpad %s", config.wallpad_manufacturer)
        transport = create_panel_transport(config)
        panel = Panel(config, mqtt_client, transport)
        return await panel.start()
    except Exception as e:
        logger.error("Failed to initialize Wallpad %s: %r", config.wallpad_manufacturer, e)
        return []


async def run_ventilator(config: AppConfig, mqtt_client: MqttClient) -> list[asyncio.Task]:
    """Ventilator 연결 및 초기화를 수행합니다. 실패 시 빈 리스트를 반환합니다."""
    if not config.ventilator_enabled:
        return []

    if config.ventilator_connection_type == "socket":
        logger.warning(
            "Ventilator socket mode is configured, but "
            "Grex implementation might require serial adapters."
        )
        return []

    try:
        logger.info("Initializing Ventilator %s", config.ventilator_manufacturer)
        ctrl_transport, unit_transport = create_ventilator_transports(config)
        ventilator = Ventilator(config, mqtt_client, ctrl_transport, unit_transport)
        return await ventilator.start()
    except Exception as e:
        logger.error("Failed to initialize Ventilator %s: %r", config.ventilator_manufacturer, e)
        return []


async def main():
    config = AppConfig()
    config.load()
    config.validate()

    setup_logging(get_log_path(), config.log_level)
    log_runtime_config(config)

    logger.info("========================================================")
    logger.info("    Wallpad MQTT Bridge Add-on  %s", SW_VERSION)
    logger.info("========================================================")

    assert config.mqtt_config is not None, "MQTT 설정이 로드되지 않았습니다."
    mqtt_client = MqttClient(config.mqtt_config)
    Bridge(mqtt_client)

    tasks = await run_panel(config, mqtt_client)
    tasks += await run_ventilator(config, mqtt_client)

    mqtt_client.connect()

    if not tasks:
        logger.error("실행할 기기가 없습니다. 종료합니다.")
        return

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
