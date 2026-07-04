# 제조사 메타데이터
MANUFACTURER = "Grex"
MODEL = "Ventilator"
IDENTIFIER_PREFIX = "grex"
NAME_PREFIX = "Grex"

# DEVICE 명명
DEVICE_FAN = "fan"

# 수신 패킷 프리픽스 (앞 2바이트)
PREFIX_CONTROLLER_ERROR = "d00a"
PREFIX_CONTROLLER_STATUS = "d08a"
PREFIX_VENTILATOR_STATUS = "d18b"

# 송신 패킷 프리픽스 (앞 4바이트)
PREFIX_CONTROL_PACKET = "d08ae022"
PREFIX_RESPONSE_PACKET = "d18be021"

# GREX 전열교환기 패킷 기본정보 (Hex -> String)
MODE = {
    "0100": "auto",
    "0200": "manual",
    "0300": "sleep",
    "0000": "off",
}
SPEED = {
    "0101": "low",
    "0202": "medium",
    "0303": "high",
    "0000": "off",
}

# String -> Hex 역매핑
MODE_HEX_MAP = {v: k for k, v in MODE.items()}
SPEED_HEX_MAP = {v: k for k, v in SPEED.items()}
