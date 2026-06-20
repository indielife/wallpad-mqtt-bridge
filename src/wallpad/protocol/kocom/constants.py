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
