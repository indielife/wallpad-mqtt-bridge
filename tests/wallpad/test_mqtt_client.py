import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from wallpad.mqtt import MqttClient, MqttConfig


def test_mqtt_client_init():
    config = MqttConfig(server="127.0.0.1", username="user", password="pwd")
    with patch("wallpad.mqtt.client.mqtt.Client") as mock_client_cls:
        client_instance = MagicMock()
        mock_client_cls.return_value = client_instance

        mqtt_client = MqttClient(config)

        assert mqtt_client.config == config
        assert mqtt_client.client == client_instance
        assert mqtt_client._connected is False
        assert mqtt_client._connect_callbacks == []
        assert mqtt_client._message_callbacks == []
        assert mqtt_client._subscribe_callbacks == []

        # Verify paho client callbacks are set
        assert client_instance.on_connect == mqtt_client._on_connect
        assert client_instance.on_message == mqtt_client._on_message
        assert client_instance.on_subscribe == mqtt_client._on_subscribe


def test_mqtt_client_connect_missing_server(caplog):
    config = MqttConfig(server="", username="user", password="pwd")
    with patch("wallpad.mqtt.client.mqtt.Client"):
        mqtt_client = MqttClient(config)
        with caplog.at_level(logging.ERROR):
            mqtt_client.connect()
        assert "Server address is missing." in caplog.text


def test_mqtt_client_connect_missing_credentials(caplog):
    config = MqttConfig(server="127.0.0.1", username="", password="")
    with patch("wallpad.mqtt.client.mqtt.Client"):
        mqtt_client = MqttClient(config)
        with caplog.at_level(logging.ERROR):
            mqtt_client.connect()
        assert "Authentication credentials are missing" in caplog.text


def test_mqtt_client_connect_success():
    config = MqttConfig(server="127.0.0.1", username="user", password="pwd")
    with patch("wallpad.mqtt.client.mqtt.Client") as mock_client_cls:
        client_instance = MagicMock()
        mock_client_cls.return_value = client_instance

        mqtt_client = MqttClient(config)
        mqtt_client.connect()

        client_instance.username_pw_set.assert_called_once_with(username="user", password="pwd")
        client_instance.connect.assert_called_once_with("127.0.0.1", 1883, 60)
        client_instance.loop_start.assert_called_once()


def test_mqtt_client_connect_exception(caplog):
    config = MqttConfig(server="127.0.0.1", username="user", password="pwd")
    with patch("wallpad.mqtt.client.mqtt.Client") as mock_client_cls:
        client_instance = MagicMock()
        client_instance.connect.side_effect = Exception("connection error")
        mock_client_cls.return_value = client_instance

        mqtt_client = MqttClient(config)
        with caplog.at_level(logging.ERROR):
            mqtt_client.connect()
        assert "Failed to connect to broker" in caplog.text


def test_mqtt_client_callbacks():
    config = MqttConfig(server="127.0.0.1", username="user", password="pwd")
    with patch("wallpad.mqtt.client.mqtt.Client"):
        mqtt_client = MqttClient(config)

        connect_cb = MagicMock()
        message_cb = MagicMock()
        subscribe_cb = MagicMock()

        mqtt_client.register_connect_callback(connect_cb)
        mqtt_client.register_message_callback(message_cb)
        mqtt_client.register_subscribe_callback(subscribe_cb)

        # Test on_connect success
        mqtt_client._on_connect(mqtt_client.client, None, {}, 0)
        assert mqtt_client._connected is True
        connect_cb.assert_called_once_with(mqtt_client.client, None, {}, 0)

        # Test on_connect failure code
        connect_cb.reset_mock()
        mqtt_client._on_connect(mqtt_client.client, None, {}, 5)
        connect_cb.assert_called_once_with(mqtt_client.client, None, {}, 5)

        # Test on_message
        msg = MagicMock()
        mqtt_client._on_message(mqtt_client.client, None, msg)
        message_cb.assert_called_once_with(mqtt_client.client, None, msg)

        # Test on_subscribe
        mqtt_client._on_subscribe(mqtt_client.client, None, 1, [0])
        subscribe_cb.assert_called_once_with(mqtt_client.client, None, 1, [0])


def test_mqtt_client_callback_exceptions(caplog):
    config = MqttConfig(server="127.0.0.1", username="user", password="pwd")
    with patch("wallpad.mqtt.client.mqtt.Client"):
        mqtt_client = MqttClient(config)

        bad_cb = MagicMock(side_effect=ValueError("bad callback"))
        good_cb = MagicMock()

        mqtt_client.register_connect_callback(bad_cb)
        mqtt_client.register_connect_callback(good_cb)

        with caplog.at_level(logging.ERROR):
            mqtt_client._on_connect(mqtt_client.client, None, {}, 0)

        assert "Error in connect callback" in caplog.text
        bad_cb.assert_called_once()
        good_cb.assert_called_once()

        # For message callback exception
        bad_msg_cb = MagicMock(side_effect=ValueError("bad msg cb"))
        good_msg_cb = MagicMock()
        mqtt_client.register_message_callback(bad_msg_cb)
        mqtt_client.register_message_callback(good_msg_cb)

        msg = MagicMock()
        with caplog.at_level(logging.ERROR):
            mqtt_client._on_message(mqtt_client.client, None, msg)

        assert "Error in message callback" in caplog.text
        bad_msg_cb.assert_called_once()
        good_msg_cb.assert_called_once()

        # For subscribe callback exception
        bad_sub_cb = MagicMock(side_effect=ValueError("bad sub cb"))
        good_sub_cb = MagicMock()
        mqtt_client.register_subscribe_callback(bad_sub_cb)
        mqtt_client.register_subscribe_callback(good_sub_cb)

        with caplog.at_level(logging.ERROR):
            mqtt_client._on_subscribe(mqtt_client.client, None, 1, [0])

        assert "Error in subscribe callback" in caplog.text
        bad_sub_cb.assert_called_once()
        good_sub_cb.assert_called_once()


def test_mqtt_client_publish_and_subscribe():
    config = MqttConfig(server="127.0.0.1", username="user", password="pwd")
    with patch("wallpad.mqtt.client.mqtt.Client") as mock_client_cls:
        client_instance = MagicMock()
        mock_client_cls.return_value = client_instance

        mqtt_client = MqttClient(config)

        # Test publish
        mqtt_client.publish("topic/test", "payload_test", retain=False)
        client_instance.publish.assert_called_once_with("topic/test", "payload_test", retain=False)

        # Test publish_json
        client_instance.publish.reset_mock()
        payload_data = {"key": "값"}
        mqtt_client.publish_json("topic/json", payload_data, retain=True)
        # Verify serialization with ensure_ascii=False
        expected_payload = json.dumps(payload_data, ensure_ascii=False)
        client_instance.publish.assert_called_once_with("topic/json", expected_payload, retain=True)

        # Test subscribe
        mqtt_client.subscribe("topic/sub", 1)
        client_instance.subscribe.assert_called_once_with("topic/sub", 1)
