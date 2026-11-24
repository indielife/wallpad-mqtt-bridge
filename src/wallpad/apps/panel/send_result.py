from enum import Enum


class SendResult(Enum):
    """송신 완료는 기기 응답 확인과 별개다."""

    SENT = "sent"
    DEFERRED = "deferred"
    INVALID = "invalid"
    FAILED = "failed"
