from unittest.mock import MagicMock

import pytest

from wallpad.ventilator.ventilator import Ventilator


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.sw_version = "0.1.0"
    config.ventilator_default_speed = "low"
    return config


@pytest.fixture
def ventilator_instance(mock_config):
    return Ventilator(mock_config, MagicMock(), MagicMock(), MagicMock())
