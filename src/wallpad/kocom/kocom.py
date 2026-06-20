import asyncio
import json
import logging
import time

from wallpad.config import AppConfig
from wallpad.kocom.devices import (
    Elevator,
    Fan,
    Gas,
    Light,
    Plug,
    Thermostat,
)
from wallpad.kocom.state import DeviceState, KocomStateManager, RoomState, ScanState, SubDeviceState
from wallpad.mqtt import (
    HA_CLIMATE,
    HA_FAN,
    HA_LIGHT,
    HA_SWITCH,
    MqttClient,
)
from wallpad.protocol.kocom.constants import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    DEVICE_WALLPAD,
    KOCOM_COMMAND,
    KOCOM_COMMAND_REV,
    KOCOM_DEVICE,
    KOCOM_DEVICE_REV,
    KOCOM_FAN_SPEED,
    KOCOM_FAN_SPEED_REV,
    KOCOM_INTERVAL,
    KOCOM_TYPE,
    KOCOM_TYPE_REV,
)
from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder
from wallpad.transport import BaseTransport

logger = logging.getLogger(__name__)  # HA MQTT Discovery

_DEVICE_TYPE_MAP = {
    DEVICE_LIGHT: Light,
    DEVICE_PLUG: Plug,
    DEVICE_THERMOSTAT: Thermostat,
    DEVICE_ELEVATOR: Elevator,
    DEVICE_GAS: Gas,
    DEVICE_FAN: Fan,
}


class Kocom:
    def __init__(  # noqa: C901
        self,
        config: AppConfig,
        mqtt_client: MqttClient,
        transport: BaseTransport,
    ):
        self.config = config
        self.transport = transport
        self.name = config.wallpad_manufacturer
        self.mqtt_client = mqtt_client

        self.default_speed = config.kocom_default_speed
        if self.default_speed not in ["low", "medium", "high"]:
            logger.info(
                "[Error] Kocom DEFAULT_SPEED 설정오류로 low로 설정. %s -> low",
                self.default_speed,
            )
            self.default_speed = "low"

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
                    name_prefix=self.name,
                    sw_version=self.config.sw_version,
                    packet_builder=self.packet_builder,
                )
            )
        if self.wp_gas:
            self.devices.append(
                Gas(
                    name_prefix=self.name,
                    sw_version=self.config.sw_version,
                    packet_builder=self.packet_builder,
                )
            )
        if self.wp_fan:
            self.devices.append(
                Fan(
                    name_prefix=self.name,
                    sw_version=self.config.sw_version,
                    packet_builder=self.packet_builder,
                )
            )
        for d_name in KOCOM_DEVICE.values():
            device_state = DeviceState()
            self.wp_list[d_name] = device_state

            if d_name in (DEVICE_ELEVATOR, DEVICE_GAS):
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
            elif d_name in (DEVICE_LIGHT, DEVICE_PLUG):
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
                    for sub_device in r_value:
                        if sub_device != "scan":
                            self.devices.append(
                                Light(
                                    name_prefix=self.name,
                                    room=room,
                                    sub_device=sub_device,
                                    sw_version=self.config.sw_version,
                                    packet_builder=self.packet_builder,
                                )
                            )

        if self.wp_plug:
            for room, r_value in self.wp_list.get(DEVICE_PLUG, {}).items():
                if isinstance(r_value, dict):
                    for sub_device in r_value:
                        if sub_device != "scan":
                            self.devices.append(
                                Plug(
                                    name_prefix=self.name,
                                    room=room,
                                    sub_device=sub_device,
                                    sw_version=self.config.sw_version,
                                    packet_builder=self.packet_builder,
                                )
                            )

        if self.wp_thermostat:
            for room in self.wp_list.get(DEVICE_THERMOSTAT, {}):
                self.devices.append(
                    Thermostat(
                        name_prefix=self.name,
                        room=room,
                        sw_version=self.config.sw_version,
                        packet_builder=self.packet_builder,
                    )
                )

        self._loop: asyncio.AbstractEventLoop | None = None
        self.mqtt_client.register_connect_callback(self.on_connect)
        self.mqtt_client.register_message_callback(self.on_message)

    async def start(self) -> list[asyncio.Task]:
        self._loop = asyncio.get_running_loop()
        await self.transport.connect()
        self._task_read = asyncio.create_task(self.get_serial(self.name, 42))
        self._task_scan = asyncio.create_task(self.scan_list())
        return [self._task_read, self._task_scan]

    def on_connect(self, *_):
        self._subscribe_ha_topics()
        self._publish_ha_discovery()

    def _subscribe_ha_topics(self):
        subscribe_list = [("wallpad/bridge/#", 0)]
        for device in self.devices:
            for topic in device.get_subscribe_topics():
                subscribe_list.append((topic, 0))
        self.mqtt_client.subscribe(subscribe_list)

    def _publish_ha_discovery(self, remove=False):
        publish_list = []
        self.ha_registry = False
        self.kocom_scan = True
        ha_topic = False

        for device in self.devices:
            for topic, payload in device.get_discovery_payloads(remove=remove):
                publish_list.append({topic: payload})
                ha_topic = topic

        for ha in publish_list:
            for topic, payload in ha.items():
                self.mqtt_client.publish(topic, payload, retain=True)

        self.ha_registry = ha_topic

    def on_message(self, client, obj, msg):  # noqa: C901
        _topic = msg.topic.split("/")
        _payload = msg.payload.decode()

        if (
            "config" in _topic
            and _topic[0] == "wallpad"
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
                self._publish_ha_discovery()
                logger.info("[From HA]HomeAssistant Restart")
                return
            elif _topic[3] == "remove":
                self._publish_ha_discovery(remove=True)
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

        if self.ha_registry is not False and self.ha_registry == msg.topic and self.kocom_scan:
            self.kocom_scan = False

    def parse_message(self, topic, payload):  # noqa: C901
        device = topic[1]
        command = topic[3]

        if command == "config":
            return

        if device in (HA_LIGHT, HA_SWITCH):
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
                        logger.warning("Cannot set GAS to ON from HA")
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

    def _find_device(self, device_type: str, room: str):
        cls = _DEVICE_TYPE_MAP.get(device_type)
        if cls is None:
            return None
        return next((d for d in self.devices if isinstance(d, cls) and d.room == room), None)

    def publish_state_to_ha(self, device_type: str, room: str, value):
        target = self._find_device(device_type, room)
        if target is None:
            return
        for topic, payload in target.get_ha_state_messages(value):
            self.mqtt_client.publish_json(topic, payload)
            logger.info("[To HA] %s = %s", topic, json.dumps(payload, ensure_ascii=False))

    async def get_serial(self, packet_name, packet_len):
        packet = ""
        start_flag = False
        while True:
            row_data = await self.transport.read(1)
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
        except Exception as e:
            logger.error("Failed to parse packet %s: %r", packet, e)
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
        except Exception as e:
            logger.error("Failed to parse value from packet %r: %r", p, e)
            return False

    def _schedule_write(self, data: str) -> None:
        if data and self._loop:
            asyncio.run_coroutine_threadsafe(
                self.transport.write(bytearray.fromhex(data)), self._loop
            )
            self.tick = time.time()

    def packet_parsing(self, packet, name="kocom", from_to="From"):
        p = self.parse_packet(packet)
        v = self.value_packet(p)

        try:
            if v["command"] == "조회" and v["src_device"] == DEVICE_WALLPAD:
                if name == "HA":
                    packet = self.make_packet(v["dst_device"], v["dst_room"], "조회", "", "")
                    self._schedule_write(packet)
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
        except Exception as e:
            logger.error(
                "Error parsing packet %s (%s %s): %r",
                packet,
                from_to,
                name,
                e,
            )

    def set_list(self, device, room, value, name="kocom"):
        try:
            logger.info("[From %s]%s/%s/state = %s", name, device, room, value)
            self.wp_list.update_from_rs485(device, room, value, self.default_speed)
        except Exception as e:
            logger.error(
                "Failed to update state from %s: %s/%s = %s (error: %r)",
                name,
                device,
                room,
                value,
                e,
            )

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

    async def _periodic_scan_room(
        self, device: str, room: str, scan: ScanState, now: float
    ) -> None:
        if now - scan.last > 2:
            scan.count += 1
            scan.last = now
            await self.set_serial(device, room, "", "", cmd="조회")
            await asyncio.sleep(self.config.packey_delay)
        if scan.count > 4:
            scan.tick = now
            scan.count = 0
            scan.last = 0

    async def _scan_sub_device(
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
            await self.set_serial(device, room, sub_d, sub_v.set)
        elif isinstance(sub_v.last, float) and now - sub_v.last > 1:
            sub_v.last = "set"
            sub_v.count += 1

    async def _scan_room(self, device: str, room: str, r_state: RoomState, now: float) -> None:
        if device == DEVICE_ELEVATOR:
            for sub_d, sub_v in r_state.sub_devices.items():
                await self._scan_sub_device(device, room, sub_d, sub_v, now)
            return

        scan = r_state.scan
        # 엘리베이터가 아닌 기기들의 주기적 스캔/조회 처리
        if now - scan.tick > self.config.scan_interval:
            await self._periodic_scan_room(device, room, scan, now)
        else:
            for sub_d, sub_v in r_state.sub_devices.items():
                await self._scan_sub_device(device, room, sub_d, sub_v, now)

    async def _perform_scan(self, now: float) -> None:
        for device, d_state in self.wp_list.items():
            if not self._is_device_enabled(device):
                continue

            for room, r_state in d_state.items():
                await self._scan_room(device, room, r_state, now)

    async def scan_list(self):
        while True:
            if not self.kocom_scan:
                now = time.time()
                if now - self.tick > KOCOM_INTERVAL / 1000:
                    try:
                        await self._perform_scan(now)
                    except Exception as e:
                        logger.debug("Scan failed: %r", e)
            await asyncio.sleep(0.2)

    async def set_serial(self, device, room, target, value, cmd="상태"):
        if (time.time() - self.tick) < KOCOM_INTERVAL / 1000:
            return

        if cmd == "상태":
            logger.info("[To %s]%s/%s/%s -> %s", self.name, device, room, target, value)
        elif cmd == "조회":
            logger.info("[To %s]%s/%s -> 조회", self.name, device, room)

        packet = (
            self.make_packet(device, room, "상태", target, value)
            if cmd == "상태"
            else self.make_packet(device, room, "조회", "", "")
        )

        if not packet:
            return

        v = self.value_packet(self.parse_packet(packet))

        logger.debug("[To %s]%s", self.name, packet)
        if v["command"] == "조회" and v["src_device"] == DEVICE_WALLPAD:
            logger.debug(
                "[To %s]%s(%s) %s(%s) -> %s(%s)",
                self.name,
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
                self.name,
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
        await self.transport.write(bytearray.fromhex(packet))
        self.tick = time.time()

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
