import asyncio
import json
import logging
from functools import partial

from wallpad.apps.panel.devices import CategoryController, Room
from wallpad.apps.panel.factory import DeviceFactory
from wallpad.apps.panel.heating_commands import HeatingCommandTracker
from wallpad.apps.panel.send_result import SendResult
from wallpad.apps.panel.synchronizer import StateSynchronizer
from wallpad.config import AppConfig
from wallpad.devices.base import BaseDevice
from wallpad.ha.discovery import HandshakeHaDiscoveryCoordinator
from wallpad.mqtt import (
    TOPIC_BRIDGE_CHECKSUM,
    TOPIC_BRIDGE_PACKET,
    TOPIC_BRIDGE_SCAN,
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
)
from wallpad.protocol.kocom.packet_builder import KocomPacketBuilder
from wallpad.protocol.kocom.parser import KocomPacketParser
from wallpad.transport.bus_arbitration import BusArbitrationTransport

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


def _log_discarded(discarded: list[str], minimum: int = 1) -> None:
    if len(discarded) >= minimum:
        logger.debug("event=rx_discard reason=resync raw=%s", "".join(discarded))
        discarded.clear()


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
        transport: BusArbitrationTransport,
    ):
        self.config = config
        self.mqtt_client = mqtt_client
        self.transport = transport

        self.name = config.wallpad_manufacturer
        self.default_speed = config.kocom_default_speed

        self.scan_packet_buf = []
        self._loop: asyncio.AbstractEventLoop | None = None

        self.packet_builder = KocomPacketBuilder(
            room_rev=config.kocom_room_rev, room_thermostat_rev=config.kocom_room_thermostat_rev
        )
        self.parser = KocomPacketParser(config)
        self.rooms, self.device_states = DeviceFactory.build(config, self.name, self.packet_builder)
        self.devices = flatten_device_tree(self.rooms)
        self.controller_map: dict[tuple[str, str], CategoryController] = {
            (controller.category, controller.room): controller
            for room in self.rooms
            for controller in room.controllers
        }
        self.heating_commands = {
            room: HeatingCommandTracker(room)
            for category, room in self.controller_map
            if category == DEVICE_THERMOSTAT
        }
        self.device_map: dict[tuple[str, str], BaseDevice] = {
            (type(d).__name__.lower(), d.room): d for d in self.devices
        }
        for room, command in self.heating_commands.items():
            command.on_change = partial(self._publish_heating_diagnostic, room)
        self.command_registry: dict[str, BaseDevice] = {
            topic: device for device in self.devices for topic in device.get_command_topics()
        }
        logger.debug("[Init] command_registry keys: %s", list(self.command_registry.keys()))

        self.ha_coordinator = HandshakeHaDiscoveryCoordinator(
            mqtt_client=self.mqtt_client,
            devices=self.devices,
            loop_provider=lambda: self._loop,
        )
        self.ha_ready = self.ha_coordinator.ha_ready

        self.mqtt_client.register_connect_callback(self.ha_coordinator.on_connect)
        self.mqtt_client.register_connect_callback(self._on_heating_reconnect)
        self._register_topic_routes()

        self.synchronizer = StateSynchronizer(
            device_states=self.device_states,
            send_packet=self.send_packet,
            config=config,
            is_bus_idle=self.transport.is_idle,
            ha_ready=self.ha_ready,
            heating_commands=self.heating_commands,
        )

    async def start(self) -> list[asyncio.Task]:
        self._loop = asyncio.get_running_loop()
        await self.transport.connect()
        self._task_read = asyncio.create_task(self.receive_packets())
        self._task_sync = asyncio.create_task(self.synchronizer.run())
        self._loop = asyncio.get_running_loop()
        return [self._task_read, self._task_sync]

    def _register_topic_routes(self) -> None:
        for device in self.devices:
            command_topics = device.get_command_topics()
            for topic in command_topics:
                self.mqtt_client.register_topic_callback(topic, self._handle_device_command)
            command_topics_set = set(command_topics)
            for topic in device.get_subscribe_topics():
                if topic not in command_topics_set:
                    self.mqtt_client.register_topic_callback(topic, self.ha_coordinator.handle_echo)

        self.ha_coordinator.register_routes()
        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_SCAN, self._handle_scan)
        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_PACKET, self._handle_packet_debug)
        self.mqtt_client.register_topic_callback(TOPIC_BRIDGE_CHECKSUM, self._handle_checksum_debug)

    def _handle_device_command(self, topic: str, payload: str) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._apply_device_command, topic, payload)
        else:
            self._apply_device_command(topic, payload)

    def _apply_device_command(self, topic: str, payload: str) -> None:
        if not self.ha_ready.is_set():
            return
        self.parse_message(topic.split("/"), payload)

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
            self.controller_map[(device_type, room)].apply_ha_command(
                sub_device, command, processed_payload, self.default_speed
            )
            if device_type == DEVICE_THERMOSTAT:
                state = self.controller_map[(device_type, room)].state
                requested = {"mode": state["mode"].set}
                if requested["mode"] == "heat":
                    requested["target_temp"] = state["target_temp"].set
                self.heating_commands[room].begin(requested)
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

    def _publish_heating_diagnostic(self, room: str, snapshot: dict) -> None:
        device = self.device_map[(DEVICE_THERMOSTAT, room)]
        assert device.topics is not None
        self.mqtt_client.publish_json(device.topics.diagnostic_state_topic, snapshot)

    def _on_heating_reconnect(self, *_) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._publish_heating_diagnostics)
        else:
            self._publish_heating_diagnostics()

    def _publish_heating_diagnostics(self) -> None:
        for room, command in self.heating_commands.items():
            self._publish_heating_diagnostic(room, command.snapshot())

    async def receive_packets(self):
        buf = []
        discarded = []

        try:
            while True:
                hex_byte = (await self.transport.read(1)).hex()
                buf.append(hex_byte)

                while len(buf) >= 2:
                    sof = buf[0] + buf[1]
                    if sof not in self.parser.SOF_LENGTH_MAP:
                        discarded.append(buf.pop(0))
                        _log_discarded(discarded, minimum=64)
                        continue

                    expected_len = self.parser.SOF_LENGTH_MAP[sof]
                    if len(buf) < expected_len:
                        break

                    packet = "".join(buf[:expected_len])
                    valid, reason = self.parser.validate_frame(packet)
                    if valid:
                        _log_discarded(discarded)
                        logger.debug("event=rx_frame raw=%s", packet)
                        self.process_packet(packet)
                        buf = buf[expected_len:]
                    else:
                        logger.debug(
                            "event=rx_discard reason=%s raw=%s expected_checksum=%s received=%s",
                            reason,
                            packet,
                            self.parser.validate_checksum(packet)[1],
                            packet[36:38],
                        )
                        discarded.append(buf.pop(0))
                        _log_discarded(discarded, minimum=64)
        finally:
            _log_discarded(discarded)
            if buf:
                logger.debug("event=rx_discard reason=incomplete raw=%s", "".join(buf))

    def process_packet(self, packet, source="kocom"):
        parsed_frame = self.parser.parse_frame(packet, self.device_states)
        if parsed_frame is None:
            logger.debug("event=frame_unhandled source=%s raw=%s", source, packet)
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
                if (
                    source == "kocom"
                    and parsed_frame["type"] == "ack"
                    and update_target["device"] == DEVICE_THERMOSTAT
                    and update_target["room"] in self.heating_commands
                    and isinstance(packet, str)
                    and self.parser.validate_frame(packet)[0]
                ):
                    self.heating_commands[update_target["room"]].observe(parsed_frame["value"])
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

    def _schedule_write(self, data: str | None) -> None:
        if data and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._write_packet(data, source="HA_debug"), self._loop
            )

    async def _write_packet(
        self, packet: str, source: str, request_id: int | None = None
    ) -> SendResult:
        try:
            sent = await self.transport.write_if_idle(bytes.fromhex(packet))
        except Exception:
            logger.exception("event=tx_failed source=%s raw=%s", source, packet)
            return SendResult.FAILED
        if not sent:
            logger.debug("event=tx_deferred source=%s reason=bus_busy raw=%s", source, packet)
            return SendResult.DEFERRED
        logger.debug("event=tx_frame source=%s request_id=%s raw=%s", source, request_id, packet)
        return SendResult.SENT

    def set_list(self, device, room, value):
        try:
            self.controller_map[(device, room)].apply_rs485_state(value, self.default_speed)
            logger.info("[From rs485] %s/%s/state = %s", device, room, value)
        except Exception as e:
            logger.error(
                "Failed to update state from rs485: %s/%s = %s (error: %r)",
                device,
                room,
                value,
                e,
            )

    async def send_packet(
        self, device, room, target, value, cmd="상태", *, request_id: int | None = None
    ) -> SendResult:
        if cmd == "상태":
            packet = self.make_packet(device, room, "상태", target, value)
        elif cmd == "조회":
            packet = self.make_packet(device, room, "조회", "", "")
        else:
            return SendResult.INVALID

        if not packet:
            logger.warning("event=tx_invalid device=%s room=%s target=%s", device, room, target)
            return SendResult.INVALID

        parsed_frame = self.parser.parse_frame(packet, self.device_states)

        result = await self._write_packet(
            packet, source="poll" if cmd == "조회" else "control", request_id=request_id
        )
        if result is not SendResult.SENT:
            return result

        if cmd == "상태":
            logger.info("[To %s] %s/%s/%s -> %s", self.name, device, room, target, value)
        else:
            logger.info("[To %s] %s/%s -> 조회", self.name, device, room)
        logger.debug("[To RS485] %s", packet)
        if parsed_frame is not None:
            log_frame("To", self.name, parsed_frame)

        if device == DEVICE_ELEVATOR:
            self.publish_state_to_ha(DEVICE_ELEVATOR, DEVICE_WALLPAD, "on")
        return SendResult.SENT

    def make_packet(self, device, room, cmd, target, value):
        # 1. (device, room) 컨트롤러에 조립 위임 (맵 조회 O(1), 타겟 탐색은 컨트롤러 책임)
        controller = self.controller_map.get((device, room))
        if controller is not None and cmd != "조회":
            built_packet = controller.make_packet(cmd, target, value)
            if built_packet:
                return built_packet

        # 2. 컨트롤러에서 처리되지 않은 공통 명령(예: 방 전체 '조회')은 빌더로 직접 생성
        if cmd == "조회":
            return self.packet_builder.build_scan_packet(device=device, room=room)

        return None
