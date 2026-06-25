import asyncio
import json
import logging

from wallpad.config import AppConfig
from wallpad.mqtt import (
    HA_FAN,
    HA_PREFIX,
    HA_SENSOR,
    MqttClient,
)
from wallpad.protocol.grex.constants import DEVICE_FAN
from wallpad.protocol.grex.packet_builder import GrexPacketBuilder
from wallpad.protocol.grex.parser import GrexPacketParser
from wallpad.transport import BaseTransport
from wallpad.ventilator.devices import GrexVentilator

logger = logging.getLogger(__name__)


class Ventilator:
    def __init__(
        self,
        config: AppConfig,
        mqtt_client: MqttClient,
        controller_transport: BaseTransport,
        ventilator_transport: BaseTransport,
    ):
        self.config = config
        self.name = "grex"
        self.controller_transport = controller_transport
        self.ventilator_transport = ventilator_transport
        self.mqtt_client = mqtt_client
        self.grex_cont = {"mode": "off", "speed": "off"}
        self.vent_cont = {"mode": "off", "speed": "off"}
        self.mqtt_cont = {"mode": "off", "speed": "off"}

        self.default_speed = config.ventilator_default_speed
        if self.default_speed not in ["low", "medium", "high"]:
            logger.info(
                "[Error] Grex DEFAULT_SPEED 설정오류로 low로 설정. %s -> low",
                self.default_speed,
            )
            self.default_speed = "low"

        self.mqtt_client.register_connect_callback(self.on_connect)
        self.mqtt_client.register_message_callback(self.on_message)
        self.packet_builder = GrexPacketBuilder()
        self._parser = GrexPacketParser()
        self.device = GrexVentilator(
            name_prefix=self.name,
            sw_version=self.config.sw_version,
            packet_builder=self.packet_builder,
        )

    async def start(self) -> list[asyncio.Task]:
        await self.controller_transport.connect()
        await self.ventilator_transport.connect()
        self._task_ctrl = asyncio.create_task(
            self.get_serial(self.controller_transport, "grex_controller", 11)
        )
        self._task_vent = asyncio.create_task(
            self.get_serial(self.ventilator_transport, "grex_ventilator", 12)
        )
        return [self._task_ctrl, self._task_vent]

    def on_connect(self, *_):
        self._subscribe_ha_topics()
        self._publish_ha_discovery()

    def _subscribe_ha_topics(self):
        subscribe_list = [("wallpad/bridge/#", 0)]
        for topic in self.device.get_subscribe_topics():
            subscribe_list.append((topic, 0))
        self.mqtt_client.subscribe(subscribe_list)

    def _publish_ha_discovery(self, remove=False):
        for topic, payload in self.device.get_discovery_payloads(remove=remove):
            self.mqtt_client.publish(topic, payload, retain=True)

    def on_message(self, client, obj, msg):
        _topic = msg.topic.split("/")
        _payload = msg.payload.decode()

        if "config" in _topic:
            if _topic[0] == "wallpad" and _topic[3] == "restart":
                self._publish_ha_discovery()
                return
        elif _topic[0] == HA_PREFIX and _topic[1] == HA_FAN and _topic[2] == "grex":
            logger.info("Message Fan: %s = %s", msg.topic, _payload)
            if _topic[3] == "speed" or _topic[3] == "mode":
                if (
                    _topic[3] == "mode"
                    and self.mqtt_cont[_topic[3]] == "off"
                    and _payload == "on"
                    and self.mqtt_cont["speed"] == "off"
                ):
                    self.mqtt_cont["speed"] = self.default_speed
                self.mqtt_cont[_topic[3]] = _payload

                if self.mqtt_cont["mode"] == "off" and self.mqtt_cont["speed"] == "off":
                    self.publish_state_to_ha(HA_FAN, self.mqtt_cont)

    def publish_state_to_ha(self, target, value):
        if target == HA_FAN:
            topic = f"{HA_PREFIX}/{HA_FAN}/grex/state"
            self.mqtt_client.publish_json(topic, value)
            logger.info("[To HA] %s = %s", topic, json.dumps(value, ensure_ascii=False))
        elif target == HA_SENSOR:
            topic = f"{HA_PREFIX}/{HA_SENSOR}/grex_{DEVICE_FAN}/state"
            self.mqtt_client.publish_json(topic, value)
            logger.info("[To HA] %s = %s", topic, json.dumps(value, ensure_ascii=False))

    async def get_serial(self, transport, packet_name, packet_len):
        buf = []
        start_flag = False
        while True:
            row_data = await transport.read(1)
            hex_d = row_data.hex()
            start_hex = ""
            if packet_name == "kocom":
                start_hex = "aa"
            elif packet_name == "grex_ventilator":
                start_hex = "d1"
            elif packet_name == "grex_controller":
                start_hex = "d0"
            if hex_d == start_hex:
                start_flag = True
            if start_flag:
                buf.append(hex_d)

            if len(buf) >= packet_len:
                joindata = "".join(buf)
                is_valid, _ = self._parser.validate_checksum(joindata)
                if is_valid:
                    await self.packet_parsing(joindata, packet_name)
                buf = []
                start_flag = False

    async def _handle_d00a(self):
        m_packet = self.device.build_response_packet("off", "off")
        is_valid, _ = self._parser.validate_checksum(m_packet)
        if is_valid:
            await self.controller_transport.write(bytearray.fromhex(m_packet))
        logger.debug("[From Grex]error code : E1")

    async def _handle_d08a(self, packet, packet_name):  # noqa: C901
        control_packet = ""
        response_packet = ""
        frame = self._parser.parse_frame(packet)
        p_mode = frame["mode"]
        p_speed = frame["speed"]

        if (
            self.grex_cont["mode"] != p_mode
            or self.grex_cont["speed"] != p_speed
        ):
            self.grex_cont["mode"] = p_mode
            self.grex_cont["speed"] = p_speed
            logger.info(
                "[From %s]mode:%s / speed:%s",
                packet_name,
                self.grex_cont["mode"],
                self.grex_cont["speed"],
            )
            send_to_ha_fan = {"mode": "off", "speed": "off"}
            if self.grex_cont["mode"] != "off" or (
                self.grex_cont["mode"] == "off" and self.mqtt_cont["mode"] == "on"
            ):
                send_to_ha_fan["mode"] = "on"
                send_to_ha_fan["speed"] = self.grex_cont["speed"]
            self.publish_state_to_ha(HA_FAN, send_to_ha_fan)

            send_to_ha_sensor = {"fan_mode": "off", "fan_speed": "off"}
            if self.grex_cont["mode"] != "off" or (
                self.grex_cont["mode"] == "off" and self.mqtt_cont["mode"] == "on"
            ):
                if self.grex_cont["mode"] == "auto":
                    send_to_ha_sensor["fan_mode"] = "자동"
                elif self.grex_cont["mode"] == "manual":
                    send_to_ha_sensor["fan_mode"] = "수동"
                elif self.grex_cont["mode"] == "sleep":
                    send_to_ha_sensor["fan_mode"] = "취침"
                elif self.grex_cont["mode"] == "off" and self.mqtt_cont["mode"] == "on":
                    send_to_ha_sensor["fan_mode"] = "HA"
                if self.grex_cont["speed"] == "low":
                    send_to_ha_sensor["fan_speed"] = "1단"
                elif self.grex_cont["speed"] == "medium":
                    send_to_ha_sensor["fan_speed"] = "2단"
                elif self.grex_cont["speed"] == "high":
                    send_to_ha_sensor["fan_speed"] = "3단"
                elif self.grex_cont["speed"] == "off":
                    send_to_ha_sensor["fan_speed"] = "대기"
            self.publish_state_to_ha(HA_SENSOR, send_to_ha_sensor)

        if self.grex_cont["mode"] == "off":
            response_packet = self.device.build_response_packet("off", "off")
            if self.mqtt_cont["mode"] == "off" or (
                self.mqtt_cont["mode"] == "on" and self.mqtt_cont["speed"] == "off"
            ):
                control_packet = self.device.build_control_packet("off", "off")
            elif self.mqtt_cont["mode"] == "on" and self.mqtt_cont["speed"] != "off":
                control_packet = self.device.build_control_packet("manual", self.mqtt_cont["speed"])
        else:
            control_packet = self.device.build_control_packet(
                self.grex_cont["mode"], self.grex_cont["speed"]
            )
            response_packet = self.device.build_response_packet(
                self.grex_cont["mode"], self.grex_cont["speed"]
            )

        if response_packet != "":
            await self.controller_transport.write(bytearray.fromhex(response_packet))
        if control_packet != "":
            await self.ventilator_transport.write(bytearray.fromhex(control_packet))

    def _handle_d18b(self, packet, packet_name):  # noqa: C901
        frame = self._parser.parse_frame(packet)
        p_speed = frame["speed"]
        if self.vent_cont["speed"] != p_speed:
            self.vent_cont["speed"] = p_speed
            logger.info("[From %s]speed:%s", packet_name, self.vent_cont["speed"])

            send_to_ha_fan = {"mode": "off", "speed": "off"}
            if self.grex_cont["mode"] != "off" or (
                self.grex_cont["mode"] == "off" and self.mqtt_cont["mode"] == "on"
            ):
                send_to_ha_fan["mode"] = "on"
                send_to_ha_fan["speed"] = self.vent_cont["speed"]
            self.publish_state_to_ha(HA_FAN, send_to_ha_fan)

            send_to_ha_sensor = {"fan_mode": "off", "fan_speed": "off"}
            if self.grex_cont["mode"] != "off" or (
                self.grex_cont["mode"] == "off" and self.mqtt_cont["mode"] == "on"
            ):
                if self.grex_cont["mode"] == "auto":
                    send_to_ha_sensor["fan_mode"] = "자동"
                elif self.grex_cont["mode"] == "manual":
                    send_to_ha_sensor["fan_mode"] = "수동"
                elif self.grex_cont["mode"] == "sleep":
                    send_to_ha_sensor["fan_mode"] = "취침"
                elif self.grex_cont["mode"] == "off" and self.mqtt_cont["mode"] == "on":
                    send_to_ha_sensor["fan_mode"] = "HA"
                if self.vent_cont["speed"] == "low":
                    send_to_ha_sensor["fan_speed"] = "1단"
                elif self.vent_cont["speed"] == "medium":
                    send_to_ha_sensor["fan_speed"] = "2단"
                elif self.vent_cont["speed"] == "high":
                    send_to_ha_sensor["fan_speed"] = "3단"
                elif self.vent_cont["speed"] == "off":
                    send_to_ha_sensor["fan_speed"] = "대기"
            self.publish_state_to_ha(HA_SENSOR, send_to_ha_sensor)

    async def packet_parsing(self, packet, packet_name):
        p_prefix = packet[:4]

        if p_prefix == "d00a":
            await self._handle_d00a()
        elif p_prefix == "d08a":
            await self._handle_d08a(packet, packet_name)
        elif p_prefix == "d18b":
            self._handle_d18b(packet, packet_name)

