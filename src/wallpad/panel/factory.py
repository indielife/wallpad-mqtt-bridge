from wallpad.config import AppConfig
from wallpad.devices.base import BaseDevice
from wallpad.panel.devices import Elevator, Fan, Gas, Light, Plug, Thermostat
from wallpad.panel.state import DeviceState, KocomStateManager, RoomState, SubDeviceState
from wallpad.panel.topic import TopicBuilder
from wallpad.protocol.kocom import constants as kocom_const
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


class DeviceFactory:
    @staticmethod
    def build(
        config: AppConfig,
        name_prefix: str,
        packet_builder: KocomPacketBuilder,
    ) -> tuple[list[BaseDevice], KocomStateManager]:
        devices: list[BaseDevice] = []
        states = KocomStateManager()

        if config.elevator_enabled:
            DeviceFactory._add_elevator(config, name_prefix, packet_builder, devices, states)
        if config.gas_enabled:
            DeviceFactory._add_gas(config, name_prefix, packet_builder, devices, states)
        if config.fan_enabled:
            DeviceFactory._add_fan(config, name_prefix, packet_builder, devices, states)

        DeviceFactory._add_room_devices(config, name_prefix, packet_builder, devices, states)

        return devices, states

    @staticmethod
    def _add_elevator(
        config: AppConfig,
        name_prefix: str,
        packet_builder: KocomPacketBuilder,
        devices: list[BaseDevice],
        states: KocomStateManager,
    ) -> None:
        topics = TopicBuilder.for_elevator(room="wallpad", sub_device="elevator")
        devices.append(
            Elevator(
                name_prefix=name_prefix,
                sw_version=config.sw_version,
                hw_info=kocom_const.HARDWARE,
                packet_builder=packet_builder,
                topics=topics,
            )
        )
        device_state = DeviceState()
        room_state = RoomState()
        room_state[DEVICE_ELEVATOR] = SubDeviceState(state="off", set_val="off")
        device_state[DEVICE_WALLPAD] = room_state
        states[DEVICE_ELEVATOR] = device_state

    @staticmethod
    def _add_gas(
        config: AppConfig,
        name_prefix: str,
        packet_builder: KocomPacketBuilder,
        devices: list[BaseDevice],
        states: KocomStateManager,
    ) -> None:
        topics = TopicBuilder.for_gas(room="wallpad", sub_device="gas")
        devices.append(
            Gas(
                name_prefix=name_prefix,
                sw_version=config.sw_version,
                hw_info=kocom_const.HARDWARE,
                packet_builder=packet_builder,
                topics=topics,
            )
        )
        device_state = DeviceState()
        room_state = RoomState()
        room_state[DEVICE_GAS] = SubDeviceState(state="off", set_val="off")
        device_state[DEVICE_WALLPAD] = room_state
        states[DEVICE_GAS] = device_state

    @staticmethod
    def _add_fan(
        config: AppConfig,
        name_prefix: str,
        packet_builder: KocomPacketBuilder,
        devices: list[BaseDevice],
        states: KocomStateManager,
    ) -> None:
        topics = TopicBuilder.for_fan(room="wallpad", sub_device="fan")
        devices.append(
            Fan(
                name_prefix=name_prefix,
                sw_version=config.sw_version,
                hw_info=kocom_const.HARDWARE,
                packet_builder=packet_builder,
                topics=topics,
            )
        )
        device_state = DeviceState()
        room_state = RoomState()
        room_state["mode"] = SubDeviceState(state="off", set_val="off")
        room_state["speed"] = SubDeviceState(state="off", set_val="off")
        device_state[DEVICE_WALLPAD] = room_state
        states[DEVICE_FAN] = device_state

    @staticmethod
    def _add_room_devices(
        config: AppConfig,
        name_prefix: str,
        packet_builder: KocomPacketBuilder,
        devices: list[BaseDevice],
        states: KocomStateManager,
    ) -> None:
        light_state = DeviceFactory._build_lights(config, name_prefix, packet_builder, devices)
        plug_state = DeviceFactory._build_plugs(config, name_prefix, packet_builder, devices)
        thermo_state = DeviceFactory._build_thermostats(
            config, name_prefix, packet_builder, devices
        )
        if light_state:
            states[DEVICE_LIGHT] = light_state
        if plug_state:
            states[DEVICE_PLUG] = plug_state
        if thermo_state:
            states[DEVICE_THERMOSTAT] = thermo_state

    @staticmethod
    def _build_lights(
        config: AppConfig,
        name_prefix: str,
        packet_builder: KocomPacketBuilder,
        devices: list[BaseDevice],
    ) -> DeviceState:
        device_state = DeviceState()
        for room in config.rooms:
            if room.light_addr is None or room.light_count == 0:
                continue
            room_state = RoomState()
            for i in range(room.light_count + 1):
                room_state[DEVICE_LIGHT + str(i)] = SubDeviceState(state="off", set_val="off")
                sub_device_name = DEVICE_LIGHT + str(i)
                topics = TopicBuilder.for_light(room=room.name, sub_device=sub_device_name)
                devices.append(
                    Light(
                        name_prefix=name_prefix,
                        room=room.name,
                        sub_device=sub_device_name,
                        sw_version=config.sw_version,
                        hw_info=kocom_const.HARDWARE,
                        packet_builder=packet_builder,
                        topics=topics,
                    )
                )
            device_state[room.name] = room_state
        return device_state

    @staticmethod
    def _build_plugs(
        config: AppConfig,
        name_prefix: str,
        packet_builder: KocomPacketBuilder,
        devices: list[BaseDevice],
    ) -> DeviceState:
        device_state = DeviceState()
        for room in config.rooms:
            if room.light_addr is None or room.plug_count == 0:
                continue
            room_state = RoomState()
            for i in range(room.plug_count + 1):
                room_state[DEVICE_PLUG + str(i)] = SubDeviceState(state="on", set_val="on")
                sub_device_name = DEVICE_PLUG + str(i)
                topics = TopicBuilder.for_plug(room=room.name, sub_device=sub_device_name)
                devices.append(
                    Plug(
                        name_prefix=name_prefix,
                        room=room.name,
                        sub_device=sub_device_name,
                        sw_version=config.sw_version,
                        hw_info=kocom_const.HARDWARE,
                        packet_builder=packet_builder,
                        topics=topics,
                    )
                )
            device_state[room.name] = room_state
        return device_state

    @staticmethod
    def _build_thermostats(
        config: AppConfig,
        name_prefix: str,
        packet_builder: KocomPacketBuilder,
        devices: list[BaseDevice],
    ) -> DeviceState:
        device_state = DeviceState()
        for room in config.rooms:
            if room.thermo_addr is None:
                continue
            room_state = RoomState()
            room_state["mode"] = SubDeviceState(state="off", set_val="off")
            room_state["current_temp"] = SubDeviceState(state=0, set_val=0)
            room_state["target_temp"] = SubDeviceState(
                state=config.init_temp, set_val=config.init_temp
            )
            device_state[room.name] = room_state
            topics = TopicBuilder.for_thermostat(room=room.name)
            devices.append(
                Thermostat(
                    name_prefix=name_prefix,
                    room=room.name,
                    sw_version=config.sw_version,
                    hw_info=kocom_const.HARDWARE,
                    packet_builder=packet_builder,
                    topics=topics,
                )
            )
        return device_state
