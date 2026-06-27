```
MQTT 메시지 수신
  topic: ["homeassistant", "light", "living_light1", "set"]
  payload: "on"
        │
        ▼
parse_message()                          [panel.py:281]
  device = topic[1] → "light" (HA_LIGHT)
  sub_device = "light1"
  sub_device.find(DEVICE_LIGHT) → device = DEVICE_LIGHT  ← 여기서 도메인 전환
        │
        ▼
device_states.update_from_ha()                 [state.py:150]
  r_state["light1"].set = "on"
  r_state["light1"].last = "set"         ← "보내야 함" 표시
        │
        ▼  (scan_list 루프에서 감지)
set_serial(DEVICE_LIGHT, room, "light1", "on")  [panel.py:636]
        │
        ▼
make_packet(DEVICE_LIGHT, ...)           [panel.py:685]
  → target_obj.build_packet(cmd="상태", target="light1", value="on", ...)
        │
        ▼
Light.build_packet()                     [devices/light.py:50]
  device_hex = device_rev["light"] → "0e"
  room_hex   = room_rev["living"]  → "11" (예)
  cmd_hex    = cmd_rev["상태"]     → "4e"
  value_hex  = "ff000000..."       ← light1만 ff, 나머지 현재 상태 반영
        │
        ▼
KocomPacketBuilder.build()               [protocol/kocom/packet_builder.py:10]
  → "aa5530bc00" + "0e" + "11" + "0100" + "4e" + "ff00..." + checksum + "0d0d"
```
