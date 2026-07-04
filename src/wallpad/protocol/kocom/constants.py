from wallpad.protocol.base import HardwareInfo

# 제조사 메타데이터
HARDWARE = HardwareInfo(
    manufacturer="KOCOM",
    model="Wallpad",
    identifier_prefix="kocom",
    name_prefix="Kocom",
)

# DEVICE 명명
DEVICE_WALLPAD = "wallpad"
DEVICE_LIGHT = "light"
DEVICE_THERMOSTAT = "thermostat"
DEVICE_PLUG = "plug"
DEVICE_GAS = "gas"
DEVICE_ELEVATOR = "elevator"
DEVICE_FAN = "fan"

# KOCOM 코콤 패킷 기본정보
KOCOM_DEVICE_BY_HEX = {
    "01": DEVICE_WALLPAD,
    "0e": DEVICE_LIGHT,
    "36": DEVICE_THERMOSTAT,
    "3b": DEVICE_PLUG,
    "44": DEVICE_ELEVATOR,
    "2c": DEVICE_GAS,
    "48": DEVICE_FAN,
}
KOCOM_COMMAND_BY_HEX = {
    "3a": "조회",
    "00": "상태",
    "01": "on",
    "02": "off",
}
KOCOM_TYPE_BY_HEX = {
    "30b": "send",
    "30d": "ack",
}
KOCOM_FAN_SPEED_BY_HEX = {
    "4": "low",
    "8": "medium",
    "c": "high",
    "0": "off",
}

KOCOM_HEX_BY_DEVICE = {v: k for k, v in KOCOM_DEVICE_BY_HEX.items()}
KOCOM_HEX_BY_COMMAND = {v: k for k, v in KOCOM_COMMAND_BY_HEX.items()}
KOCOM_HEX_BY_TYPE = {v: k for k, v in KOCOM_TYPE_BY_HEX.items()}
KOCOM_HEX_BY_FAN_SPEED = {v: k for k, v in KOCOM_FAN_SPEED_BY_HEX.items()}

# KOCOM TIME 변수
KOCOM_INTERVAL = 100
