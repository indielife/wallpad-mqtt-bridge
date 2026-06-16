import json
import logging
import threading
from typing import ClassVar

from wallpad.config import AppConfig
from wallpad.grex.devices import GrexPacketBuilder, GrexVentilator
from wallpad.mqtt import MqttClient
from wallpad.rs485 import ConnectionAdapter

logger = logging.getLogger(__name__)

HA_PREFIX = "homeassistant"
HA_SENSOR = "sensor"
HA_FAN = "fan"

DEVICE_FAN = "fan"


class Grex:
    # GREX 전열교환기 패킷 기본정보
    MODE: ClassVar[dict[str, str]] = {
        "0100": "auto",
        "0200": "manual",
        "0300": "sleep",
        "0000": "off",
    }
    SPEED: ClassVar[dict[str, str]] = {
        "0101": "low",
        "0202": "medium",
        "0303": "high",
        "0000": "off",
    }

    def __init__(
        self,
        config: AppConfig,
        controller_adapter: ConnectionAdapter,
        ventilator_adapter: ConnectionAdapter,
        mqtt_client: MqttClient,
    ):
        self.config = config
        self._name = "grex"
        self.controller_adapter = controller_adapter
        self.ventilator_adapter = ventilator_adapter
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
        self.device = GrexVentilator(
            name_prefix=self._name,
            sw_version=self.config.sw_version,
            packet_builder=self.packet_builder,
        )

        _t4 = threading.Thread(
            target=self.get_serial,
            args=(
                self.controller_adapter,
                "grex_controller",
                11,
            ),
        )
        _t4.daemon = True
        _t4.start()
        _t5 = threading.Thread(
            target=self.get_serial,
            args=(
                self.ventilator_adapter,
                "grex_ventilator",
                12,
            ),
        )
        _t5.daemon = True
        _t5.start()

    def on_message(self, client, obj, msg):
        _topic = msg.topic.split("/")
        _payload = msg.payload.decode()

        if "config" in _topic:
            if _topic[0] == "rs485" and _topic[3] == "restart":
                self.publish_ha_discovery()
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

    def on_connect(self, client, userdata, flags, rc):
        if int(rc) == 0:
            logger.info("MQTT connected OK")
            self.publish_ha_discovery(initial=True)
        elif int(rc) == 1:
            logger.info("1: Connection refused - incorrect protocol version")
        elif int(rc) == 2:
            logger.info("2: Connection refused - invalid client identifier")
        elif int(rc) == 3:
            logger.info("3: Connection refused - server unavailable")
        elif int(rc) == 4:
            logger.info("4: Connection refused - bad username or password")
        elif int(rc) == 5:
            logger.info("5: Connection refused - not authorised")
        else:
            logger.info(rc, ": Connection refused")

    def publish_ha_discovery(self, initial=False, remove=False):
        subscribe_list = []
        publish_list = []
        subscribe_list.append(("rs485/bridge/#", 0))

        for topic, payload in self.device.get_discovery_payloads(remove=remove):
            publish_list.append({topic: payload})
        for topic in self.device.get_subscribe_topics():
            subscribe_list.append((topic, 0))

        if initial:
            self.mqtt_client.subscribe(subscribe_list)
        for ha in publish_list:
            for topic, payload in ha.items():
                self.mqtt_client.publish(topic, payload, retain=True)

    def publish_state_to_ha(self, target, value):
        if target == HA_FAN:
            topic = f"{HA_PREFIX}/{HA_FAN}/grex/state"
            self.mqtt_client.publish_json(topic, value)
            logger.info("[To HA] %s = %s", topic, json.dumps(value, ensure_ascii=False))
        elif target == HA_SENSOR:
            topic = f"{HA_PREFIX}/{HA_SENSOR}/grex_{DEVICE_FAN}/state"
            self.mqtt_client.publish_json(topic, value)
            logger.info("[To HA] %s = %s", topic, json.dumps(value, ensure_ascii=False))

    def get_serial(self, adapter, packet_name, packet_len):
        buf = []
        start_flag = False
        while True:
            row_data = adapter.read()
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
                chksum = self.validate_checksum(joindata, packet_len - 1)
                if chksum[0]:
                    self.packet_parsing(joindata, packet_name)
                buf = []
                start_flag = False

    def _handle_d00a(self):
        m_packet = self.device.build_response_packet("off", "off")
        m_chksum = self.validate_checksum(m_packet, 11)
        if m_chksum[0]:
            self.controller_adapter.write(bytearray.fromhex(m_packet))
        logger.debug("[From Grex]error code : E1")

    def _handle_d08a(self, packet, packet_name):  # noqa: C901
        control_packet = ""
        response_packet = ""
        p_mode = packet[8:12]
        p_speed = packet[12:16]

        if (
            self.grex_cont["mode"] != self.MODE[p_mode]
            or self.grex_cont["speed"] != self.SPEED[p_speed]
        ):
            self.grex_cont["mode"] = self.MODE[p_mode]
            self.grex_cont["speed"] = self.SPEED[p_speed]
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
            self.controller_adapter.write(bytearray.fromhex(response_packet))
        if control_packet != "":
            self.ventilator_adapter.write(bytearray.fromhex(control_packet))

    def _handle_d18b(self, packet, packet_name):  # noqa: C901
        p_speed = packet[8:12]
        if self.vent_cont["speed"] != self.SPEED[p_speed]:
            self.vent_cont["speed"] = self.SPEED[p_speed]
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

    def packet_parsing(self, packet, packet_name):
        p_prefix = packet[:4]

        if p_prefix == "d00a":
            self._handle_d00a()
        elif p_prefix == "d08a":
            self._handle_d08a(packet, packet_name)
        elif p_prefix == "d18b":
            self._handle_d18b(packet, packet_name)

    def hex_to_list(self, hex_string):
        slide_windows = 2
        start = 0
        buf = []
        for _ in range(int(len(hex_string) / 2)):
            buf.append(f"0x{hex_string[start:slide_windows].lower()}")
            slide_windows += 2
            start += 2
        return buf

    def validate_checksum(self, packet, length):
        hex_list = self.hex_to_list(packet)
        sum_buf = 0
        for ix, x in enumerate(hex_list):
            if ix > 0:
                hex_int = int(x, 16)
                if ix == length:
                    chksum_hex = f"0x{(sum_buf % 256):02x}"
                    if hex_list[ix] == chksum_hex:
                        return (True, hex_list[ix])
                    else:
                        return (False, hex_list[ix])
                sum_buf += hex_int
