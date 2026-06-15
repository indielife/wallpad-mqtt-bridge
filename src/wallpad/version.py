import json
import logging
import os

logger = logging.getLogger(__name__)


def _get_version_from_config() -> str:
    possible_paths = [
        "/app/config.json",  # 도커 환경
        os.path.join(os.getcwd(), "config.json"),  # 로컬 개발 환경
    ]

    version_str = "0.1.0-dev"

    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    config_data = json.load(f)
                    version_str = config_data.get("version", version_str)
                break
            except Exception as e:
                logger.debug("Failed to read config from %s: %r", path, e)

    return version_str


SW_VERSION = f"RS485 Compilation {_get_version_from_config()}"
