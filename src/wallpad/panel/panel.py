import asyncio
import json
import logging

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
from wallpad.panel.devices import Room
from wallpad.panel.factory import DeviceFactory
from wallpad.panel.synchronizer import StateSynchronizer
from wallpad.protocol.kocom.constants import (
    DEVICE_ELEVATOR,
    DEVICE_FAN,
    DEVICE_GAS,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
    DEVICE_WALLPAD,
)
from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder
from wallpad.protocol.kocom.parser import KocomPacketParser
from wallpad.transport import BaseTransport

logger = logging.getLogger(__name__)  # HA MQTT Discovery

# 트리(Room→CategoryController→SubDevice)를 레거시 flat 리스트로 평면화할 때의
# 카테고리 순회 순서. discovery 발행·명령 등록 등 기존 외부 계약이 이 순서에
# 의존하므로, 카테고리-major(방 기기는 카테고리별로 전체 방을 순회)로 고정한다.
FLATTEN_CATEGORY_ORDER = (
    DEVICE_ELEVATOR,
    DEVICE_GAS,
    DEVICE_FAN,
    DEVICE_LIGHT,
    DEVICE_PLUG,
    DEVICE_THERMOSTAT,
)


def flatten_device_tree(rooms: list[Room]) -> list[BaseDevice]:
    """기기 계층 트리를 레거시 flat device 리스트로 파생한다.

    Panel 하위 로직(device_map·command_registry·discovery·make_packet)이 기대하는
    순서를 그대로 재현하기 위해 카테고리-major로 순회한다.
    """
    devices: list[BaseDevice] = []
    for category in FLATTEN_CATEGORY_ORDER:
        for room in rooms:
            controller = room.controller(category)
            if controller is not None:
                devices.extend(controller.sub_devices)
    return devices


def log_frame(direction: str, name: str, parsed_frame: dict) -> None:
    fmt = "[%s %s] %s(%s) %s(%s) -> %s(%s)"
    args = [
        direction,
        name,
        parsed_frame["type"],
        parsed_frame["command"],
        parsed_frame["src_device"],
        parsed_frame["src_room"],
        parsed_frame["dst_device"],
        parsed_frame["dst_room"],
    ]

    is_query = parsed_frame["command"] == "조회" and parsed_frame["src_device"] == DEVICE_WALLPAD
    if not is_query:
        fmt += " = %s"
        args.append(parsed_frame["value"])

    logger.debug(fmt, *args)


class Panel:
    def __init__(
        self,
        config: AppConfig,
        mqtt_client: MqttClient,
        transport: BaseTransport,
    ):
        self.config = config
        self.mqtt_client = mqtt_client
        self.transport = transport

        self.name = config.wallpad_manufacturer
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

        self.packet_builder = KocomPacketBuilder(
            room_rev=config.kocom_room_rev, room_thermostat_rev=config.kocom_room_thermostat_rev
        )
        self.parser = KocomPacketParser(config)
        self.rooms, self.device_states = DeviceFactory.build(config, self.name, self.packet_builder)
        self.devices = flatten_device_tree(self.rooms)
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

        self.synchronizer = StateSynchronizer(
            device_states=self.device_states,
            send_packet=self.send_packet,
            config=config,
            is_bus_idle=self.transport.is_idle,
            ha_ready=self.ha_ready,
        )

    async def start(self) -> list[asyncio.Task]:
        await self.transport.connect()
        self._task_read = asyncio.create_task(self.receive_packets())
        self._task_sync = asyncio.create_task(self.synchronizer.run())
        self._loop = asyncio.get_running_loop()
        return [self._task_read, self._task_sync]

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
        self.process_packet(payload.lower(), source="HA")

    def _handle_checksum_debug(self, topic: str, payload: str) -> None:
        chksum = self.parser.validate_checksum(payload.lower())
        logger.info("[From HA] %s = %s(%s)", payload, chksum[0], chksum[1])

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
                "[From HA] %s/%s/%s/%s = %s",
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
        buf = []
        while True:
            hex_byte = (await self.transport.read(1)).hex()
            buf.append(hex_byte)

            while len(buf) >= 2:
                sof = buf[0] + buf[1]
                if sof not in self.parser.SOF_LENGTH_MAP:
                    buf.pop(0)
                    continue

                expected_len = self.parser.SOF_LENGTH_MAP[sof]
                if len(buf) < expected_len:
                    break

                packet = "".join(buf[:expected_len])
                if self.parser.validate_checksum(packet)[0]:
                    self.process_packet(packet)
                    buf = buf[expected_len:]
                else:
                    buf.pop(0)

    def process_packet(self, packet, source="kocom"):
        parsed_frame = self.parser.parse_frame(packet, self.device_states)
        if parsed_frame is None:
            return

        try:
            if (
                parsed_frame["command"] == "조회"
                and parsed_frame["src_device"] == DEVICE_WALLPAD
                and source == "HA"
            ):
                packet = self.make_packet(
                    parsed_frame["dst_device"], parsed_frame["dst_room"], "조회", "", ""
                )
                self._schedule_write(packet)
            log_frame("From", source, parsed_frame)

            update_target = parsed_frame.get("update_target")
            if update_target:
                self.set_list(update_target["device"], update_target["room"], parsed_frame["value"])
                self.publish_state_to_ha(
                    update_target["device"], update_target["room"], parsed_frame["value"]
                )
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
                self.transport.write_if_idle(bytearray.fromhex(data)), self._loop
            )

    def set_list(self, device, room, value):
        try:
            self.device_states.update_from_rs485(device, room, value, self.default_speed)
            logger.info("[From rs485] %s/%s/state = %s", device, room, value)
        except Exception as e:
            logger.error(
                "Failed to update state from rs485: %s/%s = %s (error: %r)",
                device,
                room,
                value,
                e,
            )

    async def send_packet(self, device, room, target, value, cmd="상태"):
        if cmd == "상태":
            packet = self.make_packet(device, room, "상태", target, value)
        elif cmd == "조회":
            packet = self.make_packet(device, room, "조회", "", "")
        else:
            return

        if not packet:
            return

        parsed_frame = self.parser.parse_frame(packet, self.device_states)

        if not await self.transport.write_if_idle(bytearray.fromhex(packet)):
            return

        if cmd == "상태":
            logger.info("[To %s] %s/%s/%s -> %s", self.name, device, room, target, value)
        else:
            logger.info("[To %s] %s/%s -> 조회", self.name, device, room)
        logger.debug("[To RS485] %s", packet)
        log_frame("To", self.name, parsed_frame)

        if device == DEVICE_ELEVATOR:
            self.publish_state_to_ha(DEVICE_ELEVATOR, DEVICE_WALLPAD, "on")

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
