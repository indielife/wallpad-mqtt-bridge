"""방 단위 난방 요청과 실제 수신 상태의 확인 기록.

응답의 인과관계나 물리적 난방 동작을 보장하지 않는다. 송신 이후 받은 유효 상태가
요청값과 일치하는지만 확인한다. 재시도 횟수·간격 정책은 동기화 워커가 소유한다.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from wallpad.apps.panel.send_result import SendResult

logger = logging.getLogger(__name__)


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


@dataclass
class HeatingCommandTracker:
    room: str
    on_change: Callable[[dict], None] | None = field(default=None, repr=False)
    request_id: int = 0
    status: str = "idle"
    requested: dict[str, str | int] = field(default_factory=dict)
    requested_at: str | None = None
    attempts: int = 0
    waiting_since: float | None = None
    last_sent_at: str | None = None
    last_received: dict[str, str | int] | None = None
    last_received_at: str | None = None
    reason: str | None = None
    confirmed_late: bool = False
    _observations: int = 0
    _send_observation: int = 0
    _first_send_observation: int | None = None
    _last_emitted: dict | None = field(default=None, repr=False)

    def snapshot(self) -> dict:
        return {
            "request_id": self.request_id,
            "status": self.status,
            "requested": dict(self.requested),
            "requested_at": self.requested_at,
            "attempts": self.attempts,
            "last_sent_at": self.last_sent_at,
            "last_received": dict(self.last_received) if self.last_received is not None else None,
            "last_received_at": self.last_received_at,
            "reason": self.reason,
            "confirmed_late": self.confirmed_late,
        }

    def begin(self, requested: dict[str, str | int]) -> None:
        if self.status == "pending":
            self._log("superseded")
        self.request_id += 1
        self.status = "pending"
        self.requested = dict(requested)
        self.requested_at = _timestamp()
        self.attempts = 0
        self.waiting_since = None
        self.last_sent_at = None
        self.reason = None
        self.confirmed_late = False
        self._first_send_observation = None
        self._log("requested")

    def start_send(self) -> int:
        self._send_observation = self._observations
        return self.request_id

    def finish_send(self, request_id: int, result: SendResult) -> None:
        if request_id != self.request_id:
            logger.info(
                "event=heating_superseded_write room=%s request_id=%s result=%s",
                self.room,
                request_id,
                result.value,
            )
            return
        if result is SendResult.SENT:
            self.attempts += 1
            self.last_sent_at = _timestamp()
            if self._first_send_observation is None:
                self._first_send_observation = self._send_observation
            if self.status == "pending":
                self.waiting_since = time.monotonic()
                self.reason = None
            self._log("sent")
            self._confirm_if_matching()
        elif self.status == "pending":
            if result is SendResult.DEFERRED:
                self.reason = "bus_busy"
                self._emit()
            else:
                self.mark_unconfirmed(result.value)

    def observe(self, value: dict[str, str | int]) -> None:
        self._observations += 1
        self.last_received = dict(value)
        self.last_received_at = _timestamp()
        self._confirm_if_matching()
        self._emit()

    def timeout(self, *, exhausted: bool) -> None:
        self.waiting_since = None
        self.reason = "response_timeout"
        self._log("response_timeout")
        if exhausted:
            self.mark_unconfirmed("retry_exhausted")

    def mark_unconfirmed(self, reason: str) -> None:
        self.status = "unconfirmed"
        self.reason = reason
        self.waiting_since = None
        self._log("unconfirmed", level=logging.WARNING)

    def _confirm_if_matching(self) -> None:
        if (
            self.status not in ("pending", "unconfirmed")
            or self._first_send_observation is None
            or self._observations <= self._first_send_observation
            or self.last_received is None
        ):
            return
        if all(self.last_received.get(k) == v for k, v in self.requested.items()):
            self.confirmed_late = self.status == "unconfirmed"
            self.status = "confirmed"
            self.reason = None
            self.waiting_since = None
            self._log("confirmed")

    def _log(self, event: str, *, level: int = logging.INFO) -> None:
        logger.log(
            level,
            "event=heating_%s room=%s request_id=%s status=%s requested=%s "
            "attempts=%s reason=%s late=%s last_received=%s last_received_at=%s",
            event,
            self.room,
            self.request_id,
            self.status,
            self.requested,
            self.attempts,
            self.reason,
            self.confirmed_late,
            self.last_received,
            self.last_received_at,
        )
        self._emit()

    def _emit(self) -> None:
        snapshot = self.snapshot()
        if self.on_change is not None and snapshot != self._last_emitted:
            self.on_change(snapshot)
            self._last_emitted = snapshot
