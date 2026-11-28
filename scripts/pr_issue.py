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


def _body_blocks(body: str) -> list[tuple[int | None, str]]:
    """인용문을 제외하고 본문 최상위 제목의 수준과 문단을 구분해 보존한다."""
    tokens = MarkdownIt("commonmark").parse(body)
    blocks: list[tuple[int | None, str]] = []
    quote_depth = 0
    for index, token in enumerate(tokens):
        if token.type == "blockquote_open":
            quote_depth += 1
        elif token.type == "blockquote_close":
            quote_depth -= 1
        elif token.type == "inline" and quote_depth == 0:
            previous = tokens[index - 1]
            heading_level = None
            if previous.type == "heading_open":
                if previous.level != 0:
                    continue
                heading_level = int(previous.tag[1:])
            blocks.append((heading_level, _reference_text(token)))
    return blocks


def _related_blocks(blocks: list[tuple[int | None, str]]) -> list[tuple[int | None, str]]:
    """실제 Related issues 제목부터 다음 동급 이상 제목까지 선택한다."""
    start = next(
        (
            (index + 1, level)
            for index, (level, text) in enumerate(blocks)
            if level is not None and text.strip().casefold() == "related issues"
        ),
        None,
    )
    if start is None:
        return blocks
    first, section_level = start
    end = next(
        (
            index
            for index, (level, _) in enumerate(blocks[first:], start=first)
            if level is not None and level <= section_level
        ),
        len(blocks),
    )
    return blocks[first:end]


def referenced_issue(body: str) -> str | None:
    """Related issues를 우선하며, 구형 본문의 독립된 참조 줄도 지원한다."""
    for heading_level, text in _related_blocks(_body_blocks(body)):
        if heading_level is not None:
            continue
        for line in text.splitlines():
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
