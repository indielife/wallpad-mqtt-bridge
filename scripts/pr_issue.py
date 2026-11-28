"""PR 본문의 실제 참조 항목에서 제목 검사에 사용할 첫 이슈를 찾는다."""

import re
import sys

from markdown_it import MarkdownIt
from markdown_it.token import Token


def _reference_text(token: Token) -> str:
    """참조 후보의 줄 경계를 보존하고 코드·HTML을 참조로 이어 붙이지 않는다."""
    parts: list[str] = []
    for child in token.children or []:
        if child.type == "text":
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append("\n")
        elif child.type in {"code_inline", "html_inline", "image"}:
            # 코드를 삭제하면 뒤의 설명이 줄 시작의 참조로 바뀔 수 있다.
            parts.append("\ufffc")
    return "".join(parts)


def _visible_lines(body: str) -> list[str]:
    """CommonMark 토큰에서 코드·HTML 블록을 제외한 본문과 제목을 읽는다."""
    tokens = MarkdownIt("commonmark").parse(body)
    lines: list[str] = []
    for index, token in enumerate(tokens):
        if token.type != "inline":
            continue
        text = _reference_text(token)
        previous = tokens[index - 1]
        if previous.type == "heading_open":
            text = "#" * int(previous.tag[1:]) + " " + text
        lines.extend(text.splitlines())
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
