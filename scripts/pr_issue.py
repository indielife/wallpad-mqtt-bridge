"""PR 본문의 실제 참조 항목에서 제목 검사에 사용할 첫 이슈를 찾는다."""

import re
import sys


def _visible_lines(body: str) -> list[str]:
    """주석과 코드 블록을 제외한 줄을 반환한다."""
    body = re.sub(r"<!--.*?(?:-->|$)", "", body, flags=re.DOTALL)
    lines: list[str] = []
    fence: str | None = None
    for line in body.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence is not None:
            if (
                marker
                and marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                fence = None
            continue
        if marker:
            fence = marker[1]
            continue
        if line.startswith(("    ", "\t")):
            continue
        lines.append(line)

    return lines


def referenced_issue(body: str) -> str | None:
    """Related issues를 우선하며, 구형 본문의 독립된 참조 줄도 지원한다."""
    lines = _visible_lines(body)
    start = None
    level = 0
    for index, line in enumerate(lines):
        heading = re.fullmatch(r" {0,3}(#{1,6})\s+Related issues\s*#*\s*", line, re.I)
        if heading:
            start, level = index + 1, len(heading[1])
            break
    candidates: list[str] = lines
    if start is not None:
        candidates = []
        for line in lines[start:]:
            heading = re.match(r" {0,3}(#{1,6})\s+", line)
            if heading and len(heading[1]) <= level:
                break
            candidates.append(line)

    for line in candidates:
        match = re.match(
            r" {0,3}(?:(?:[-+*]|\d+[.)])\s+)?(?:closes|refs?)\s+#(\d+)\b",
            line,
            re.I,
        )
        if match:
            return match[1]
    return None


if __name__ == "__main__":
    print(referenced_issue(sys.stdin.read()) or "")
