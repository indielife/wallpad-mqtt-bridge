import logging
import os
import re

logger = logging.getLogger(__name__)

_VERSION_PATTERN = re.compile(r'^version:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)


def _get_version_from_config() -> str:
    possible_paths = [
        "/app/config.yaml",  # 도커 환경
        os.path.join(os.getcwd(), "config.yaml"),  # 로컬 개발 환경
    ]

    version_str = "0.1.0-dev"

    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    match = _VERSION_PATTERN.search(f.read())
                    if match:
                        version_str = match.group(1)
                break
            except Exception as e:
                logger.debug("Failed to read config from %s: %r", path, e)

    return version_str


SW_VERSION = _get_version_from_config()
