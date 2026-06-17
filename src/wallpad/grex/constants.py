DEVICE_FAN = "fan"

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
