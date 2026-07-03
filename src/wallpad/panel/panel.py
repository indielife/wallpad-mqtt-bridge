import asyncio
import json
import logging
import time

from wallpad.config import AppConfig
from wallpad.devices.base import BaseDevice
from wallpad.mqtt import (
    TOPIC_BRIDGE_CHECKSUM,
    TOPIC_BRIDGE_PACKET,
    TOPIC_BRIDGE_REMOVE,
    TOPIC_BRIDGE_RESTART,
    TOPIC_BRIDGE_SCAN,
    MqttClient,
)
from wallpad.panel.factory import DeviceFactory
from wallpad.panel.state import RoomState, ScanState, SubDeviceState
from wallpad.protocol.kocom.constants import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    DEVICE_WALLPAD,
    KOCOM_INTERVAL,
)
from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder
from wallpad.protocol.kocom.parser import KocomPacketParser
from wallpad.transport import BaseTransport

logger = logging.getLogger(__name__)  # HA MQTT Discovery


class Panel:
    def __init__(
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
        self.ha_ready = asyncio.Event()
        self.scan_packet_buf = []

        self.tick = time.time()
        self.packet_builder = KocomPacketBuilder(
            room_rev=config.kocom_room_rev, room_thermostat_rev=config.kocom_room_thermostat_rev
        )
        self.parser = KocomPacketParser(config)
        self.devices, self.device_states = DeviceFactory.build(
            config, self.name, self.packet_builder
        )
        self.device_map: dict[tuple[str, str], BaseDevice] = {
            (type(d).__name__.lower(), d.room): d for d in self.devices
        }
        self.command_registry: dict[str, BaseDevice] = {
            topic: device for device in self.devices for topic in device.get_command_topics()
        }
        logger.debug("[Init] command_registry keys: %s", list(self.command_registry.keys()))

        self._loop: asyncio.AbstractEventLoop | None = None
        self.mqtt_client.register_connect_callback(self.on_connect)
        self._register_topic_routes()

    async def start(self) -> list[asyncio.Task]:
        await self.transport.connect()
        self._task_read = asyncio.create_task(self.receive_packets())
        self._task_scan = asyncio.create_task(self.scan_list())
        self._loop = asyncio.get_running_loop()
        return [self._task_read, self._task_scan]

    def on_connect(self, *_):
        self._publish_ha_discovery()

    def _register_topic_routes(self) -> None:
        for device in self.devices:
            command_topics = device.get_command_topics()
            for topic in command_topics:
                self.mqtt_client.register_topic_callback(topic, self._handle_device_command)
            command_topics_set = set(command_topics)
            for topic in device.get_subscribe_topics():
                if topic not in command_topics_set:
                    self.mqtt_client.register_topic_callback(topic, self._handle_discovery_echo)

        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_RESTART, self._handle_restart)
        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_REMOVE, self._handle_remove)
        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_SCAN, self._handle_scan)
        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_PACKET, self._handle_packet_debug)
        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_CHECKSUM, self._handle_checksum_debug)

    def _publish_ha_discovery(self, remove=False):
        publish_list = []
        self.ha_registry = False
        self.ha_ready.clear()
        ha_topic = False

        for device in self.devices:
            for topic, payload in device.get_discovery_payloads(remove=remove):
                publish_list.append({topic: payload})
                ha_topic = topic

        for ha in publish_list:
            for topic, payload in ha.items():
                self.mqtt_client.publish(topic, payload, retain=True)

        self.ha_registry = ha_topic

    def _handle_device_command(self, topic: str, payload: str) -> None:
        if not self.ha_ready.is_set():
            return
        self.parse_message(topic.split("/"), payload)

    def _handle_discovery_echo(self, topic: str, payload: str) -> None:
        logger.info("Message: %s = %s", topic, payload)
        if self.ha_registry is not False and self.ha_registry == topic and self._loop:
            self._loop.call_soon_threadsafe(self.ha_ready.set)

    def _handle_restart(self, topic: str, payload: str) -> None:
        self._publish_ha_discovery()
        logger.info("[From HA]HomeAssistant Restart")

    def _handle_remove(self, topic: str, payload: str) -> None:
        self._publish_ha_discovery(remove=True)
        logger.info("[From HA]HomeAssistant Remove")

    def _handle_scan(self, topic: str, payload: str) -> None:
        self.device_states.reset_scan_states()
        logger.info("[From HA]HomeAssistant Scan")

    def _handle_packet_debug(self, topic: str, payload: str) -> None:
        self.packet_parsing(payload.lower(), source="HA")

    def _handle_checksum_debug(self, topic: str, payload: str) -> None:
        chksum = self.parser.validate_checksum(payload.lower())
        logger.info("[From HA]%s = %s(%s)", payload, chksum[0], chksum[1])

    def parse_message(self, topic_parts: list[str], payload: str) -> None:
        topic_str = "/".join(topic_parts)
        device = self.command_registry.get(topic_str)
        if device is None:
            return
        command = topic_parts[-1]
        result = device.resolve_command(command, payload)
        if result is None:
            return
        device_type, room, sub_device, processed_payload = result
        try:
            self.device_states.update_from_ha(
                device_type, room, sub_device, command, processed_payload, self.default_speed
            )
            logger.info(
                "[From HA]%s/%s/%s/%s = %s",
                device_type,
                room,
                sub_device,
                command,
                processed_payload,
            )
            immediate = device.get_optimistic_state(self.device_states)
            if immediate is not None:
                self.publish_state_to_ha(device_type, room, immediate)
        except Exception as e:
            logger.error("[From HA] %s = %s, %r", topic_parts, payload, e)

    def publish_state_to_ha(self, device_type: str, room: str, value):
        target = self.device_map.get((device_type, room))
        if target is None:
            return
        for topic, payload in target.get_ha_state_messages(value):
            self.mqtt_client.publish_json(topic, payload)
            logger.info("[To HA] %s = %s", topic, json.dumps(payload, ensure_ascii=False))

    async def receive_packets(self):
        frame_buf = []
        frame_len = 0
        in_frame = False
        while True:
            byte_hex = (await self.transport.read(1)).hex()

            if byte_hex in self.parser.PACKET_FRAMES:
                frame_buf = [byte_hex]
                frame_len = self.parser.PACKET_FRAMES[byte_hex]
                in_frame = True
            elif in_frame:
                frame_buf.append(byte_hex)

            if not in_frame or len(frame_buf) < frame_len:
                continue

            packet = "".join(frame_buf)
            if self.parser.validate_checksum(packet)[0]:
                self.tick = time.time()
                self.packet_parsing(packet)

            frame_buf = []
            frame_len = 0
            in_frame = False

    def packet_parsing(self, packet, source="kocom"):
        v = self.parser.parse_frame(packet, self.device_states)

        if v is None:
            return

        try:
            if v["command"] == "조회" and v["src_device"] == DEVICE_WALLPAD:
                if source == "HA":
                    packet = self.make_packet(v["dst_device"], v["dst_room"], "조회", "", "")
                    self._schedule_write(packet)
                logger.debug(
                    "[From %s]%s(%s) %s(%s) -> %s(%s)",
                    source,
                    v["type"],
                    v["command"],
                    v["src_device"],
                    v["src_room"],
                    v["dst_device"],
                    v["dst_room"],
                )
            else:
                logger.debug(
                    "[From %s]%s(%s) %s(%s) -> %s(%s) = %s",
                    source,
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
                "Error parsing packet %s (From %s): %r",
                packet,
                source,
                e,
            )

    def _schedule_write(self, data: str) -> None:
        if data and self._loop:
            asyncio.run_coroutine_threadsafe(
                self.transport.write(bytearray.fromhex(data)), self._loop
            )
            self.tick = time.time()

    def set_list(self, device, room, value, name="kocom"):
        try:
            logger.info("[From %s]%s/%s/state = %s", name, device, room, value)
            self.device_states.update_from_rs485(device, room, value, self.default_speed)
        except Exception as e:
            logger.error(
                "Failed to update state from %s: %s/%s = %s (error: %r)",
                name,
                device,
                room,
                value,
                e,
            )

    async def _periodic_scan_room(
        self, device: str, room: str, scan: ScanState, now: float
    ) -> None:
        if now - scan.last > 2:
            scan.count += 1
            scan.last = now
            await self.send_packet(device, room, "", "", cmd="조회")
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
            await self.send_packet(device, room, sub_d, sub_v.set)
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
        for device, d_state in self.device_states.items():
            for room, r_state in d_state.items():
                await self._scan_room(device, room, r_state, now)

    async def scan_list(self):
        await self.ha_ready.wait()
        while True:
            now = time.time()
            if now - self.tick > KOCOM_INTERVAL / 1000:
                try:
                    await self._perform_scan(now)
                except Exception as e:
                    logger.debug("Scan failed: %r", e)
            await asyncio.sleep(0.2)

    async def send_packet(self, device, room, target, value, cmd="상태"):
        if (time.time() - self.tick) < KOCOM_INTERVAL / 1000:
            return

        if cmd == "상태":
            logger.info("[To %s]%s/%s/%s -> %s", self.name, device, room, target, value)
            packet = self.make_packet(device, room, "상태", target, value)
        elif cmd == "조회":
            logger.info("[To %s]%s/%s -> 조회", self.name, device, room)
            packet = self.make_packet(device, room, "조회", "", "")
        else:
            return

        if not packet:
            return

        v = self.parser.parse_frame(packet, self.device_states)

        logger.debug("[To RS485] %s", packet)
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
            room_state = self.device_states.get(device, {}).get(room, {})
            built_packet = target_obj.build_packet(
                cmd=cmd,
                target=target,
                value=value,
                room_state=room_state,
            )
            if built_packet:
                return built_packet

        # 3. 객체에서 처리되지 않은 공통 명령(예: 방 전체 '조회')은 빌더를 통해 직접 생성
        if cmd == "조회":
            return self.packet_builder.build_scan_packet(device=device, room=room)

        return None
