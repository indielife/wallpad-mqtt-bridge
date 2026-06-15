import json
import logging
import os
import os.path
import threading
import time

import paho.mqtt.client as mqtt

from kocom.config import AppConfig
from kocom.devices import (
    Elevator,
    Fan,
    Gas,
    GrexPacketBuilder,
    GrexVentilator,
    KocomPacketBuilder,
    Light,
    Plug,
    Thermostat,
)
from kocom.rs485 import CONF_MQTT
from kocom.state import DeviceState, KocomStateManager, RoomState, ScanState, SubDeviceState

logger = logging.getLogger(__name__)


# HA MQTT Discovery
HA_PREFIX = "homeassistant"
HA_SWITCH = "switch"
HA_LIGHT = "light"
HA_CLIMATE = "climate"
HA_SENSOR = "sensor"
HA_FAN = "fan"

# DEVICE 명명
DEVICE_WALLPAD = "wallpad"
DEVICE_LIGHT = "light"
DEVICE_THERMOSTAT = "thermostat"
DEVICE_PLUG = "plug"
DEVICE_GAS = "gas"
DEVICE_ELEVATOR = "elevator"
DEVICE_FAN = "fan"

# KOCOM 코콤 패킷 기본정보
KOCOM_DEVICE = {
    "01": DEVICE_WALLPAD,
    "0e": DEVICE_LIGHT,
    "36": DEVICE_THERMOSTAT,
    "3b": DEVICE_PLUG,
    "44": DEVICE_ELEVATOR,
    "2c": DEVICE_GAS,
    "48": DEVICE_FAN,
}
KOCOM_COMMAND = {"3a": "조회", "00": "상태", "01": "on", "02": "off"}
KOCOM_TYPE = {"30b": "send", "30d": "ack"}
KOCOM_FAN_SPEED = {"4": "low", "8": "medium", "c": "high", "0": "off"}
KOCOM_DEVICE_REV = {v: k for k, v in KOCOM_DEVICE.items()}
KOCOM_COMMAND_REV = {v: k for k, v in KOCOM_COMMAND.items()}
KOCOM_TYPE_REV = {v: k for k, v in KOCOM_TYPE.items()}
KOCOM_FAN_SPEED_REV = {v: k for k, v in KOCOM_FAN_SPEED.items()}

# KOCOM TIME 변수
KOCOM_INTERVAL = 100
VENTILATOR_INTERVAL = 150


class Kocom:
    def __init__(self, config: AppConfig, client, name, device, packet_len):
        self.config = config
        self.client = client
        self._name = name
        self.connected = True

        self.default_speed = config.default_speed
        if self.default_speed not in ["low", "medium", "high"]:
            logger.info(
                "[Error] Kocom DEFAULT_SPEED 설정오류로 medium 으로 설정. %s -> medium",
                self.default_speed,
            )
            self.default_speed = "medium"

        self.ha_registry = False
        self.kocom_scan = True
        self.scan_packet_buf = []

        self.tick = time.time()
        self.wp_list = KocomStateManager()
        self.wp_light = self.config.wp_light
        self.wp_fan = self.config.wp_fan
        self.wp_plug = self.config.wp_plug
        self.wp_gas = self.config.wp_gas
        self.wp_elevator = self.config.wp_elevator
        self.wp_thermostat = self.config.wp_thermostat

        self.packet_builder = KocomPacketBuilder()

        self.devices = []
        if self.wp_elevator:
            self.devices.append(
                Elevator(
                    name_prefix=self._name,
                    sw_version=self.config.sw_version,
                    packet_builder=self.packet_builder,
                )
            )
        if self.wp_gas:
            self.devices.append(
                Gas(
                    name_prefix=self._name,
                    sw_version=self.config.sw_version,
                    packet_builder=self.packet_builder,
                )
            )
        if self.wp_fan:
            self.devices.append(
                Fan(
                    name_prefix=self._name,
                    sw_version=self.config.sw_version,
                    packet_builder=self.packet_builder,
                )
            )
        for d_name in KOCOM_DEVICE.values():
            device_state = DeviceState()
            self.wp_list[d_name] = device_state

            if d_name == DEVICE_ELEVATOR or d_name == DEVICE_GAS:
                room_state = RoomState()
                room_state[d_name] = SubDeviceState(state="off", set_val="off")
                device_state[DEVICE_WALLPAD] = room_state
            elif d_name == DEVICE_FAN:
                room_state = RoomState()
                room_state["mode"] = SubDeviceState(state="off", set_val="off")
                room_state["speed"] = SubDeviceState(state="off", set_val="off")
                device_state[DEVICE_WALLPAD] = room_state
            elif d_name == DEVICE_THERMOSTAT:
                for r_name in self.config.kocom_room_thermostat.values():
                    room_state = RoomState()
                    room_state["mode"] = SubDeviceState(state="off", set_val="off")
                    room_state["current_temp"] = SubDeviceState(state=0, set_val=0)
                    room_state["target_temp"] = SubDeviceState(
                        state=self.config.init_temp, set_val=self.config.init_temp
                    )
                    device_state[r_name] = room_state
            elif d_name == DEVICE_LIGHT or d_name == DEVICE_PLUG:
                for r_name in self.config.kocom_room.values():
                    room_state = RoomState()
                    if d_name == DEVICE_LIGHT:
                        for i in range(0, self.config.kocom_light_size.get(r_name, 0) + 1):
                            room_state[d_name + str(i)] = SubDeviceState(state="off", set_val="off")
                    elif d_name == DEVICE_PLUG:
                        for i in range(0, self.config.kocom_plug_size.get(r_name, 0) + 1):
                            room_state[d_name + str(i)] = SubDeviceState(state="on", set_val="on")
                    device_state[r_name] = room_state

        if self.wp_light:
            for room, r_value in self.wp_list.get(DEVICE_LIGHT, {}).items():
                if isinstance(r_value, dict):
                    for sub_device in r_value.keys():
                        if sub_device != "scan":
                            self.devices.append(
                                Light(
                                    name_prefix=self._name,
                                    room=room,
                                    sub_device=sub_device,
                                    sw_version=self.config.sw_version,
                                    packet_builder=self.packet_builder,
                                )
                            )

        if self.wp_plug:
            for room, r_value in self.wp_list.get(DEVICE_PLUG, {}).items():
                if isinstance(r_value, dict):
                    for sub_device in r_value.keys():
                        if sub_device != "scan":
                            self.devices.append(
                                Plug(
                                    name_prefix=self._name,
                                    room=room,
                                    sub_device=sub_device,
                                    sw_version=self.config.sw_version,
                                    packet_builder=self.packet_builder,
                                )
                            )

        if self.wp_thermostat:
            for room in self.wp_list.get(DEVICE_THERMOSTAT, {}).keys():
                self.devices.append(
                    Thermostat(
                        name_prefix=self._name,
                        room=room,
                        sw_version=self.config.sw_version,
                        packet_builder=self.packet_builder,
                    )
                )

        self.d_type = client._type
        if self.d_type == "serial":
            self.d_serial = client._connect[device]
        elif self.d_type == "socket":
            self.d_serial = client._connect
        self.d_mqtt = self.connect_mqtt(self.config.mqtt_config, name)

        self._t1 = threading.Thread(target=self.get_serial, args=(name, packet_len))
        self._t1.start()
        self._t2 = threading.Thread(target=self.scan_list)
        self._t2.start()

    def connection_lost(self):
        self._t1.join()
        self._t2.join()
        if not self.connected:
            logger.debug("[ERROR] 서버 연결이 끊어져 kocom 클래스를 종료합니다.")
            return False

    def read(self):
        if self.client._connect == False:
            return ""
        try:
            if self.d_type == "serial":
                if self.d_serial.readable():
                    return self.d_serial.read()
                else:
                    return ""
            elif self.d_type == "socket":
                return self.d_serial.recv(1)
        except:
            logging.info("[Serial Read] Connection Error")

    def write(self, data):
        if not data:
            return
        self.tick = time.time()
        if self.client._connect == False:
            return
        try:
            if self.d_type == "serial":
                return self.d_serial.write(bytearray.fromhex(data))
            elif self.d_type == "socket":
                return self.d_serial.send(bytearray.fromhex(data))
        except:
            logging.info("[Serial Write] Connection Error")

    def connect_mqtt(self, server, name):
        mqtt_client = mqtt.Client()
        mqtt_client.on_message = self.on_message
        # mqtt_client.on_publish = self.on_publish
        mqtt_client.on_subscribe = self.on_subscribe
        mqtt_client.on_connect = self.on_connect

        if server["anonymous"] != "True":
            if server["server"] == "" or server["username"] == "" or server["password"] == "":
                logger.info(
                    "%s 설정을 확인하세요. Server[%s] ID[%s] PW[%s] Device[%s]",
                    CONF_MQTT,
                    server["server"],
                    server["username"],
                    server["password"],
                    name,
                )
                return False
            mqtt_client.username_pw_set(username=server["username"], password=server["password"])
            logger.debug(
                "%s STATUS. Server[%s] ID[%s] PW[%s] Device[%s]",
                CONF_MQTT,
                server["server"],
                server["username"],
                server["password"],
                name,
            )
        else:
            logger.debug("%s STATUS. Server[%s] Device[%s]", CONF_MQTT, server["server"], name)

        mqtt_client.connect(server["server"], 1883, 60)
        mqtt_client.loop_start()
        return mqtt_client

    def on_message(self, client, obj, msg):
        _topic = msg.topic.split("/")
        _payload = msg.payload.decode()

        if (
            "config" in _topic
            and _topic[0] == "rs485"
            and _topic[1] == "bridge"
            and _topic[2] == "config"
        ):
            if _topic[3] == "log_level":
                if _payload == "info":
                    logger.setLevel(logging.INFO)
                if _payload == "debug":
                    logger.setLevel(logging.DEBUG)
                if _payload == "warn":
                    logger.setLevel(logging.WARN)
                logger.info("[From HA]Set Loglevel to %s", _payload)
                return
            elif _topic[3] == "restart":
                self.publish_ha_discovery()
                logger.info("[From HA]HomeAssistant Restart")
                return
            elif _topic[3] == "remove":
                self.publish_ha_discovery(remove=True)
                logger.info("[From HA]HomeAssistant Remove")
                return
            elif _topic[3] == "scan":
                self.wp_list.reset_scan_states()
                logger.info("[From HA]HomeAssistant Scan")
                return
            elif _topic[3] == "packet":
                self.packet_parsing(_payload.lower(), name="HA")
                return
            elif _topic[3] == "check_sum":
                chksum = self.check_sum(_payload.lower())
                logger.info("[From HA]%s = %s(%s)", _payload, chksum[0], chksum[1])
                return
        elif not self.kocom_scan:
            if len(_topic) < 4:
                logger.warning(
                    "[MQTT] 길이가 짧은 예외 토픽 진입 차단: %s = %s", msg.topic, _payload
                )
                return

            self.parse_message(_topic, _payload)
            return
        logger.info("Message: %s = %s", msg.topic, _payload)

        if self.ha_registry != False and self.ha_registry == msg.topic and self.kocom_scan:
            self.kocom_scan = False

    def parse_message(self, topic, payload):
        device = topic[1]
        command = topic[3]

        if command == "config":
            return

        if device == HA_LIGHT or device == HA_SWITCH:
            room_device = topic[2].rsplit("_", 1)
            room = room_device[0]
            sub_device = room_device[1]
            if sub_device.find(DEVICE_LIGHT) != -1:
                device = DEVICE_LIGHT
            if sub_device.find(DEVICE_PLUG) != -1:
                device = DEVICE_PLUG
            if sub_device.find(DEVICE_ELEVATOR) != -1:
                device = DEVICE_ELEVATOR
            if sub_device.find(DEVICE_GAS) != -1:
                device = DEVICE_GAS
            try:
                if device == DEVICE_GAS:
                    if payload == "on":
                        payload = "off"
                        logger.info("[From HA]Error GAS Cannot Set to ON")
                    else:
                        self.wp_list.update_from_ha(
                            device, room, sub_device, command, payload, self.default_speed
                        )
                elif device == DEVICE_ELEVATOR:
                    self.wp_list.update_from_ha(
                        device, room, sub_device, command, payload, self.default_speed
                    )
                    if payload == "off":
                        self.publish_state_to_ha(device, DEVICE_WALLPAD, payload)
                else:
                    self.wp_list.update_from_ha(
                        device, room, sub_device, command, payload, self.default_speed
                    )
                logger.info("[From HA]%s/%s/%s/%s = %s", device, room, sub_device, command, payload)
            except Exception as e:
                logger.error("[From HA] %s = %s, %r", topic, payload, e)
        elif device == HA_CLIMATE:
            device = DEVICE_THERMOSTAT
            room = topic[2]
            try:
                self.wp_list.update_from_ha(device, room, "", command, payload, self.default_speed)
                room_state = self.wp_list[device][room]
                ha_payload = {
                    "mode": room_state["mode"]["set"],
                    "target_temp": room_state["target_temp"]["set"],
                    "current_temp": room_state["current_temp"]["state"],
                }
                logger.info(
                    "[From HA]%s/%s/set = [mode=%s, target_temp=%s]",
                    device,
                    room,
                    room_state["mode"]["set"],
                    room_state["target_temp"]["set"],
                )
                self.publish_state_to_ha(device, room, ha_payload)
            except Exception as e:
                logger.error("[From HA] %s = %s, %r", topic, payload, e)
        elif device == HA_FAN:
            device = DEVICE_FAN
            room = topic[2]
            try:
                self.wp_list.update_from_ha(device, room, "", command, payload, self.default_speed)
                room_state = self.wp_list[device][room]
                ha_payload = {
                    "mode": room_state["mode"]["set"],
                    "speed": room_state["speed"]["set"],
                }
                logger.info(
                    "[From HA]%s/%s/set = [mode=%s, speed=%s]",
                    device,
                    room,
                    room_state["mode"]["set"],
                    room_state["speed"]["set"],
                )
                self.publish_state_to_ha(device, room, ha_payload)
            except Exception as e:
                logger.error("[From HA] %s = %s, %r", topic, payload, e)

    def on_publish(self, client, obj, mid):
        logger.info("Publish: %s", str(mid))

    def on_subscribe(self, client, obj, mid, granted_qos):
        logger.info("Subscribed: %s %s", str(mid), str(granted_qos))

    def on_connect(self, client, userdata, flags, rc):
        if int(rc) == 0:
            logger.info("[MQTT] connected OK")
            client.subscribe("homeassistant/status")
            self.publish_ha_discovery(initial=True)
        elif int(rc) == 1:
            logger.info("[MQTT] 1: Connection refused – incorrect protocol version")
        elif int(rc) == 2:
            logger.info("[MQTT] 2: Connection refused – invalid client identifier")
        elif int(rc) == 3:
            logger.info("[MQTT] 3: Connection refused – server unavailable")
        elif int(rc) == 4:
            logger.info("[MQTT] 4: Connection refused – bad username or password")
        elif int(rc) == 5:
            logger.info("[MQTT] 5: Connection refused – not authorised")
        else:
            logger.info("[MQTT] %s : Connection refused", rc)

    def publish_ha_discovery(self, initial=False, remove=False):
        subscribe_list = []
        subscribe_list.append(("rs485/bridge/#", 0))
        publish_list = []

        self.ha_registry = False
        self.kocom_scan = True
        ha_topic = False  # 초기화 보장

        # 분리된 기기(Elevator, Gas, Fan) 객체들의 디스커버리 페이로드 생성
        for device in self.devices:
            for topic, payload in device.get_discovery_payloads(remove=remove):
                publish_list.append({topic: payload})
                ha_topic = topic
            for topic in device.get_subscribe_topics():
                subscribe_list.append((topic, 0))

        if initial:
            self.d_mqtt.subscribe(subscribe_list)

        for ha in publish_list:
            for topic, payload in ha.items():
                self.d_mqtt.publish(topic, payload, retain=True)

        self.ha_registry = ha_topic

    def publish_state_to_ha(self, device, room, value):
        payload = json.dumps(value)
        if device == DEVICE_LIGHT:
            topic = f"{HA_PREFIX}/{HA_LIGHT}/{room}/state"
            self.d_mqtt.publish(topic, payload, retain=True)
            logger.info("[To HA] %s = %s", topic, payload)
        elif device == DEVICE_PLUG:
            topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}/state"
            self.d_mqtt.publish(topic, payload, retain=True)
            logger.info("[To HA] %s = %s", topic, payload)
        elif device == DEVICE_THERMOSTAT:
            topic = f"{HA_PREFIX}/{HA_CLIMATE}/{room}/state"
            self.d_mqtt.publish(topic, payload, retain=True)
            logger.info("[To HA] %s = %s", topic, payload)
        elif device == DEVICE_ELEVATOR:
            payload = json.dumps({device: value})
            topic = f"{HA_PREFIX}/{HA_SWITCH}/{room}/state"
            self.d_mqtt.publish(topic, payload, retain=True)
            logger.info("[To HA] %s = %s", topic, payload)
        elif device == DEVICE_GAS:
            payload = json.dumps({device: value})
            topic_sensor = f"{HA_PREFIX}/{HA_SENSOR}/{room}_{DEVICE_GAS}/state"
            self.d_mqtt.publish(topic_sensor, payload, retain=True)
            logger.info("[To HA] %s = %s", topic_sensor, payload)

            topic_switch = f"{HA_PREFIX}/{HA_SWITCH}/{room}_{DEVICE_GAS}/state"
            self.d_mqtt.publish(topic_switch, payload, retain=True)
            logger.info("[To HA] %s = %s", topic_switch, payload)
        elif device == DEVICE_FAN:
            topic = f"{HA_PREFIX}/{HA_FAN}/{room}/state"
            self.d_mqtt.publish(topic, payload, retain=True)
            logger.info("[To HA] %s = %s", topic, payload)

    def get_serial(self, packet_name, packet_len):
        packet = ""
        start_flag = False
        while True:
            row_data = self.read()
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
                packet += hex_d

            if len(packet) >= packet_len:
                chksum = self.check_sum(packet)
                if chksum[0]:
                    self.tick = time.time()
                    logger.debug("[From %s]%s", packet_name, packet)
                    self.packet_parsing(packet)
                packet = ""
                start_flag = False
            if not self.connected:
                logger.debug("[ERROR] 서버 연결이 끊어져 get_serial Thread를 종료합니다.")
                break

    def check_sum(self, packet):
        sum_packet = sum(bytearray.fromhex(packet)[:17])
        v_sum = int(packet[34:36], 16) if len(packet) >= 36 else 0
        chk_sum = f"{(sum_packet + 1 + v_sum) % 256:02x}"
        orgin_sum = packet[36:38] if len(packet) >= 38 else ""
        return (True, chk_sum) if chk_sum == orgin_sum else (False, chk_sum)

    def parse_packet(self, packet):
        p = {}
        try:
            p["header"] = packet[:4]
            p["type"] = packet[4:7]
            p["order"] = packet[7:8]
            if KOCOM_TYPE.get(p["type"]) == "send":
                p["dst_device"] = packet[10:12]
                p["dst_room"] = packet[12:14]
                p["src_device"] = packet[14:16]
                p["src_room"] = packet[16:18]
            elif KOCOM_TYPE.get(p["type"]) == "ack":
                p["src_device"] = packet[10:12]
                p["src_room"] = packet[12:14]
                p["dst_device"] = packet[14:16]
                p["dst_room"] = packet[16:18]
            p["command"] = packet[18:20]
            p["value"] = packet[20:36]
            p["checksum"] = packet[36:38]
            p["tail"] = packet[38:42]
            return p
        except:
            return False

    def value_packet(self, p):
        v = {}
        if not p:
            return False
        try:
            v["type"] = KOCOM_TYPE.get(p["type"])
            v["command"] = KOCOM_COMMAND.get(p["command"])
            v["src_device"] = KOCOM_DEVICE.get(p["src_device"])
            v["src_room"] = (
                self.config.kocom_room.get(p["src_room"])
                if v["src_device"] != DEVICE_THERMOSTAT
                else self.config.kocom_room_thermostat.get(p["src_room"])
            )
            v["dst_device"] = KOCOM_DEVICE.get(p["dst_device"])
            v["dst_room"] = (
                self.config.kocom_room.get(p["dst_room"])
                if v["src_device"] != DEVICE_THERMOSTAT
                else self.config.kocom_room_thermostat.get(p["dst_room"])
            )
            v["value"] = p["value"]
            if v["src_device"] == DEVICE_FAN:
                v["value"] = self.parse_fan(p["value"])
            elif v["src_device"] == DEVICE_LIGHT or v["src_device"] == DEVICE_PLUG:
                v["value"] = self.parse_switch(v["src_device"], v["src_room"], p["value"])
            elif v["src_device"] == DEVICE_THERMOSTAT:
                v["value"] = self.parse_thermostat(
                    p["value"],
                    self.wp_list[v["src_device"]][v["src_room"]]["target_temp"]["state"],
                )
            elif v["src_device"] == DEVICE_WALLPAD and v["dst_device"] == DEVICE_ELEVATOR:
                v["value"] = "off"
            elif v["src_device"] == DEVICE_GAS:
                v["value"] = v["command"]
            return v
        except:
            return False

    def packet_parsing(self, packet, name="kocom", from_to="From"):
        p = self.parse_packet(packet)
        v = self.value_packet(p)

        try:
            if v["command"] == "조회" and v["src_device"] == DEVICE_WALLPAD:
                if name == "HA":
                    self.write(self.make_packet(v["dst_device"], v["dst_room"], "조회", "", ""))
                logger.debug(
                    "[%s %s]%s(%s) %s(%s) -> %s(%s)",
                    from_to,
                    name,
                    v["type"],
                    v["command"],
                    v["src_device"],
                    v["src_room"],
                    v["dst_device"],
                    v["dst_room"],
                )
            else:
                logger.debug(
                    "[%s %s]%s(%s) %s(%s) -> %s(%s) = %s",
                    from_to,
                    name,
                    v["type"],
                    v["command"],
                    v["src_device"],
                    v["src_room"],
                    v["dst_device"],
                    v["dst_room"],
                    v["value"],
                )

            if (v["type"] == "ack" and v["dst_device"] == DEVICE_WALLPAD) or (
                v["type"] == "send" and v["dst_device"] == DEVICE_ELEVATOR
            ):
                if v["type"] == "send" and v["dst_device"] == DEVICE_ELEVATOR:
                    self.set_list(v["dst_device"], DEVICE_WALLPAD, v["value"])
                    self.publish_state_to_ha(v["dst_device"], DEVICE_WALLPAD, v["value"])
                elif v["src_device"] == DEVICE_FAN or v["src_device"] == DEVICE_GAS:
                    self.set_list(v["src_device"], DEVICE_WALLPAD, v["value"])
                    self.publish_state_to_ha(v["src_device"], DEVICE_WALLPAD, v["value"])
                elif (
                    v["src_device"] == DEVICE_THERMOSTAT
                    or v["src_device"] == DEVICE_LIGHT
                    or v["src_device"] == DEVICE_PLUG
                ):
                    self.set_list(v["src_device"], v["src_room"], v["value"])
                    self.publish_state_to_ha(v["src_device"], v["src_room"], v["value"])
        except:
            logger.info("[%s %s]Error %s", from_to, name, packet)

    def set_list(self, device, room, value, name="kocom"):
        try:
            logger.info("[From %s]%s/%s/state = %s", name, device, room, value)
            self.wp_list.update_from_rs485(device, room, value, self.default_speed)
        except Exception as e:
            logger.info("[From %s]Error SetList %s/%s = %s (%r)", name, device, room, value, e)

    def _is_device_enabled(self, device: str) -> bool:
        if device == DEVICE_ELEVATOR:
            return self.wp_elevator
        if device == DEVICE_FAN:
            return self.wp_fan
        if device == DEVICE_GAS:
            return self.wp_gas
        if device == DEVICE_LIGHT:
            return self.wp_light
        if device == DEVICE_PLUG:
            return self.wp_plug
        if device == DEVICE_THERMOSTAT:
            return self.wp_thermostat
        return False

    def _periodic_scan_room(self, device: str, room: str, scan: ScanState, now: float) -> None:
        if now - scan.last > 2:
            scan.count += 1
            scan.last = now
            self.set_serial(device, room, "", "", cmd="조회")
            time.sleep(self.config.packey_delay)
        if scan.count > 4:
            scan.tick = now
            scan.count = 0
            scan.last = 0

    def _scan_sub_device(
        self, device: str, room: str, sub_d: str, sub_v: SubDeviceState, now: float
    ) -> None:
        if sub_v.count > 4:
            sub_v.count = 0
            sub_v.last = "state"
        elif sub_v.last == "set":
            sub_v.last = now
            if device == DEVICE_GAS:
                sub_v.last += 5
            elif device == DEVICE_ELEVATOR:
                sub_v.last = "state"
            self.set_serial(device, room, sub_d, sub_v.set)
        elif isinstance(sub_v.last, float) and now - sub_v.last > 1:
            sub_v.last = "set"
            sub_v.count += 1

    def _scan_room(self, device: str, room: str, r_state: RoomState, now: float) -> None:
        if device == DEVICE_ELEVATOR:
            for sub_d, sub_v in r_state.sub_devices.items():
                self._scan_sub_device(device, room, sub_d, sub_v, now)
            return

        scan = r_state.scan
        # 엘리베이터가 아닌 기기들의 주기적 스캔/조회 처리
        if now - scan.tick > self.config.scan_interval:
            self._periodic_scan_room(device, room, scan, now)
        else:
            for sub_d, sub_v in r_state.sub_devices.items():
                self._scan_sub_device(device, room, sub_d, sub_v, now)

    def _perform_scan(self, now: float) -> None:
        for device, d_state in self.wp_list.items():
            if not self._is_device_enabled(device):
                continue

            for room, r_state in d_state.items():
                self._scan_room(device, room, r_state, now)

    def scan_list(self):
        while True:
            if not self.kocom_scan:
                now = time.time()
                if now - self.tick > KOCOM_INTERVAL / 1000:
                    try:
                        self._perform_scan(now)
                    except Exception as e:
                        logger.debug("[Scan]Error: %r", e)
            if not self.connected:
                logger.debug("[ERROR] 서버 연결이 끊어져 scan_list Thread를 종료합니다.")
                break
            time.sleep(0.2)

    def set_serial(self, device, room, target, value, cmd="상태"):
        if (time.time() - self.tick) < KOCOM_INTERVAL / 1000:
            return

        if cmd == "상태":
            logger.info("[To %s]%s/%s/%s -> %s", self._name, device, room, target, value)
        elif cmd == "조회":
            logger.info("[To %s]%s/%s -> 조회", self._name, device, room)

        packet = (
            self.make_packet(device, room, "상태", target, value)
            if cmd == "상태"
            else self.make_packet(device, room, "조회", "", "")
        )

        if not packet:
            return

        v = self.value_packet(self.parse_packet(packet))

        logger.debug("[To %s]%s", self._name, packet)
        if v["command"] == "조회" and v["src_device"] == DEVICE_WALLPAD:
            logger.debug(
                "[To %s]%s(%s) %s(%s) -> %s(%s)",
                self._name,
                v["type"],
                v["command"],
                v["src_device"],
                v["src_room"],
                v["dst_device"],
                v["dst_room"],
            )
        else:
            logger.debug(
                "[To %s]%s(%s) %s(%s) -> %s(%s) = %s",
                self._name,
                v["type"],
                v["command"],
                v["src_device"],
                v["src_room"],
                v["dst_device"],
                v["dst_room"],
                v["value"],
            )
        if device == DEVICE_ELEVATOR:
            self.publish_state_to_ha(DEVICE_ELEVATOR, DEVICE_WALLPAD, "on")
        self.write(packet)

    def make_packet(self, device, room, cmd, target, value):
        # 1. 타겟 기기 객체 찾기
        target_obj = None
        for d in self.devices:
            if device in [DEVICE_LIGHT, DEVICE_PLUG]:
                if d.room == room and d.sub_device == target:
                    target_obj = d
                    break
            elif device == DEVICE_THERMOSTAT:
                if d.room == room and d.sub_device == "thermostat":
                    target_obj = d
                    break
            else:
                if d.room == room and d.sub_device == device:
                    target_obj = d
                    break

        # 2. 객체에게 패킷 생성 위임 (전략 패턴 + 빌더)
        if target_obj and cmd != "조회":
            room_state = self.wp_list.get(device, {}).get(room, {})
            built_packet = target_obj.build_packet(
                cmd=cmd,
                target=target,
                value=value,
                room_state=room_state,
                device_rev=KOCOM_DEVICE_REV,
                room_rev=self.config.kocom_room_rev,
                cmd_rev=KOCOM_COMMAND_REV,
                room_thermostat_rev=self.config.kocom_room_thermostat_rev,
                fan_speed_rev=KOCOM_FAN_SPEED_REV,
            )
            if built_packet:
                return built_packet

        # 3. 객체에서 처리되지 않은 공통 명령(예: 방 전체 '조회')은 빌더를 통해 직접 생성
        if cmd == "조회":
            return self.packet_builder.build_scan_packet(
                device=device,
                room=room,
                device_rev=KOCOM_DEVICE_REV,
                room_rev=self.config.kocom_room_rev,
                room_thermostat_rev=self.config.kocom_room_thermostat_rev,
                cmd_rev=KOCOM_COMMAND_REV,
            )

        return None

    def parse_fan(self, value="0000000000000000"):
        fan = {}
        fan["mode"] = "on" if value[:2] == "11" else "off"
        fan["speed"] = KOCOM_FAN_SPEED.get(value[4:5])
        return fan

    def parse_switch(self, device, room, value="0000000000000000"):
        switch = {}
        on_count = 0
        to_i = (
            # KOCOM_LIGHT_SIZE.get(room) + 1
            # if device == DEVICE_LIGHT
            # else KOCOM_PLUG_SIZE.get(room) + 1
            self.config.kocom_light_size.get(room, 0) + 1
            if device == DEVICE_LIGHT
            else self.config.kocom_plug_size.get(room, 0) + 1
        )
        for i in range(1, to_i):
            switch[device + str(i)] = "off" if value[i * 2 - 2 : i * 2] == "00" else "on"
            if value[i * 2 - 2 : i * 2] != "00":
                on_count += 1
        switch[device + "0"] = "on" if on_count > 0 else "off"
        return switch

    def parse_thermostat(self, value="0000000000000000", init_temp=False):
        thermo = {}
        heat_mode = "heat" if value[:2] == "11" else "off"
        away_mode = "on" if value[2:4] == "01" else "off"
        thermo["current_temp"] = int(value[8:10], 16)
        if heat_mode == "heat" and away_mode == "on":
            thermo["mode"] = "fan_only"
            thermo["target_temp"] = self.config.init_temp if not init_temp else int(init_temp)
        elif heat_mode == "heat" and away_mode == "off":
            thermo["mode"] = "heat"
            thermo["target_temp"] = int(value[4:6], 16)
        elif heat_mode == "off":
            thermo["mode"] = "off"
            thermo["target_temp"] = self.config.init_temp if not init_temp else int(init_temp)
        return thermo


class Grex:
    # GREX 전열교환기 패킷 기본정보
    MODE = {"0100": "auto", "0200": "manual", "0300": "sleep", "0000": "off"}
    SPEED = {"0101": "low", "0202": "medium", "0303": "high", "0000": "off"}

    def __init__(self, config: AppConfig, client, cont, vent):
        self.config = config
        self._name = "grex"
        self.contoller = cont
        self.ventilator = vent
        self.grex_cont = {"mode": "off", "speed": "off"}
        self.vent_cont = {"mode": "off", "speed": "off"}
        self.mqtt_cont = {"mode": "off", "speed": "off"}

        self.default_speed = config.default_speed
        if self.default_speed not in ["low", "medium", "high"]:
            logger.info(
                "[Error] Grex DEFAULT_SPEED 설정오류로 medium 으로 설정. %s -> medium",
                self.default_speed,
            )
            self.default_speed = "medium"

        self.d_mqtt = self.connect_mqtt(self.config.mqtt_config, "GREX")
        self.packet_builder = GrexPacketBuilder()
        self.device = GrexVentilator(
            name_prefix=self._name,
            sw_version=self.config.sw_version,
            packet_builder=self.packet_builder,
        )

        _t4 = threading.Thread(
            target=self.get_serial,
            args=(
                self.contoller["serial"],
                self.contoller["name"],
                self.contoller["length"],
            ),
        )
        _t4.daemon = True
        _t4.start()
        _t5 = threading.Thread(
            target=self.get_serial,
            args=(
                self.ventilator["serial"],
                self.ventilator["name"],
                self.ventilator["length"],
            ),
        )
        _t5.daemon = True
        _t5.start()

    def connect_mqtt(self, server, name):
        mqtt_client = mqtt.Client()
        mqtt_client.on_message = self.on_message
        # mqtt_client.on_publish = self.on_publish
        mqtt_client.on_subscribe = self.on_subscribe
        mqtt_client.on_connect = self.on_connect

        if server["anonymous"] != "True":
            if server["server"] == "" or server["username"] == "" or server["password"] == "":
                logger.info(
                    "%s 설정을 확인하세요. Server[%s] ID[%s] PW[%s] Device[%s]",
                    CONF_MQTT,
                    server["server"],
                    server["username"],
                    server["password"],
                    name,
                )
                return False
            mqtt_client.username_pw_set(username=server["username"], password=server["password"])
            logger.debug(
                "%s STATUS. Server[%s] ID[%s] PW[%s] Device[%s]",
                CONF_MQTT,
                server["server"],
                server["username"],
                server["password"],
                name,
            )
        else:
            logger.debug("%s STATUS. Server[%s] Device[%s]", CONF_MQTT, server["server"], name)

        mqtt_client.connect(server["server"], 1883, 60)
        mqtt_client.loop_start()
        return mqtt_client

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

    def on_publish(self, client, obj, mid):
        logger.info("Publish: %s", str(mid))

    def on_subscribe(self, client, obj, mid, granted_qos):
        logger.info("Subscribed: %s %s", str(mid), str(granted_qos))

    def on_connect(self, client, userdata, flags, rc):
        if int(rc) == 0:
            logger.info("MQTT connected OK")
            self.publish_ha_discovery(initial=True)
        elif int(rc) == 1:
            logger.info("1: Connection refused – incorrect protocol version")
        elif int(rc) == 2:
            logger.info("2: Connection refused – invalid client identifier")
        elif int(rc) == 3:
            logger.info("3: Connection refused – server unavailable")
        elif int(rc) == 4:
            logger.info("4: Connection refused – bad username or password")
        elif int(rc) == 5:
            logger.info("5: Connection refused – not authorised")
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
            self.d_mqtt.subscribe(subscribe_list)
        for ha in publish_list:
            for topic, payload in ha.items():
                self.d_mqtt.publish(topic, payload, retain=True)

    def publish_state_to_ha(self, target, value):
        if target == HA_FAN:
            payload = json.dumps(value)
            topic = f"{HA_PREFIX}/{HA_FAN}/grex/state"
            self.d_mqtt.publish(topic, payload, retain=True)
            logger.info("[To HA] %s = %s", topic, payload)
        elif target == HA_SENSOR:
            payload = json.dumps(value, ensure_ascii=False)
            topic = f"{HA_PREFIX}/{HA_SENSOR}/grex_{DEVICE_FAN}/state"
            self.d_mqtt.publish(topic, payload, retain=True)
            logger.info("[To HA] %s = %s", topic, payload)

    def get_serial(self, ser, packet_name, packet_len):
        buf = []
        start_flag = False
        while True:
            if ser.readable():
                row_data = ser.read()
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
                if start_flag == True:
                    buf.append(hex_d)

                if len(buf) >= packet_len:
                    joindata = "".join(buf)
                    chksum = self.validate_checksum(joindata, packet_len - 1)
                    # logger.debug("[From %s]%s %s %s", packet_name, joindata, str(chksum[0]), str(chksum[1]))
                    if chksum[0]:
                        self.packet_parsing(joindata, packet_name)
                    buf = []
                    start_flag = False

    def packet_parsing(self, packet, packet_name):
        p_prefix = packet[:4]

        if p_prefix == "d00a":
            m_packet = self.device.build_response_packet("off", "off")
            m_chksum = self.validate_checksum(m_packet, 11)
            if m_chksum[0]:
                self.contoller["serial"].write(bytearray.fromhex(m_packet))
            logger.debug("[From Grex]error code : E1")
        elif p_prefix == "d08a":
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
                    control_packet = self.device.build_control_packet(
                        "manual", self.mqtt_cont["speed"]
                    )
            else:
                control_packet = self.device.build_control_packet(
                    self.grex_cont["mode"], self.grex_cont["speed"]
                )
                response_packet = self.device.build_response_packet(
                    self.grex_cont["mode"], self.grex_cont["speed"]
                )

            if response_packet != "":
                self.contoller["serial"].write(bytearray.fromhex(response_packet))
                # logger.debug("[Tooo grex_controller]%s", response_packet)
            if control_packet != "":
                self.ventilator["serial"].write(bytearray.fromhex(control_packet))
                # logger.debug("[Tooo grex_ventilator]%s", control_packet)

        elif p_prefix == "d18b":
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

    def hex_to_list(self, hex_string):
        slide_windows = 2
        start = 0
        buf = []
        for x in range(int(len(hex_string) / 2)):
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
