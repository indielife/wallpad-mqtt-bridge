"""PR 제목을 커밋 제목 규칙(`<emoji> <type>(<scope>): <subject>`)으로 정규화한다.

squash 머지 커밋에 남을 제목의 형식을 검사한다.
타입별 이모지와 중복 번호는 보정하고, scope는 작성자가 명시한다.

이모지-타입 매핑의 SoT는 commit-msg 훅이 쓰는 cz-conventional-gitmoji 테이블이다.
"""

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from shared.utils import get_gitmojis

TITLE_PATTERN = re.compile(
    r"""
    ^
    (?:(?P<icon>[^\w\s]\S*)[ ]+)?   # gitmoji — 없으면 타입에서 도출해 채운다
    (?P<type>[a-z][a-z-]*)          # 커밋 타입
    (?:\((?P<scope>[^()]+)\))?      # PR scope — 누락 시 review에서 위반을 안내한다
    (?P<breaking>!)?                # breaking change 표시
    :[ ]+
    (?P<subject>\S.*)
    $
    """,
    re.VERBOSE,
)

# squash 머지 시 GitHub이 `(#N)`을 자동으로 붙이므로 PR 제목에 직접 쓰면 중복된다.
PR_NUMBER_SUFFIX_PATTERN = re.compile(r"\s*\(#\d+\)\s*$")


@dataclass(frozen=True)
class Title:
    icon: str | None
    type: str
    scope: str | None
    breaking: bool
    subject: str

    def render(self) -> str:
        icon = f"{self.icon} " if self.icon else ""
        scope = f"({self.scope})" if self.scope else ""
        breaking = "!" if self.breaking else ""
        return f"{icon}{self.type}{scope}{breaking}: {self.subject}"


@dataclass(frozen=True)
class Outcome:
    """보정 결과. `title`은 적용할 제목, `errors`는 사람이 직접 고쳐야 하는 위반."""

    title: str
    notes: list[str] = field(default_factory=list[str])
    errors: list[str] = field(default_factory=list[str])


def icons_by_type() -> dict[str, str]:
    return {gitmoji.type: gitmoji.icon for gitmoji in get_gitmojis()}


def parse(title: str) -> Title | None:
    match = TITLE_PATTERN.match(title.strip())
    if match is None:
        return None
    return Title(
        icon=match["icon"],
        type=match["type"],
        scope=match["scope"],
        breaking=match["breaking"] is not None,
        subject=match["subject"].strip(),
    )


def review(title: str) -> Outcome:
    notes: list[str] = []
    errors: list[str] = []

    original = title.strip()
    stripped = PR_NUMBER_SUFFIX_PATTERN.sub("", original)
    if stripped != original:
        notes.append("제목 끝의 (#N)을 지웠다 — squash 머지 시 GitHub이 자동으로 붙인다")

    parsed = parse(stripped)
    if parsed is None:
        errors.append(
            f"'{original}'은 커밋 제목 형식이 아니다 — `<emoji> <type>(<scope>): <subject>`로 쓴다"
        )
        return Outcome(title=original, notes=notes, errors=errors)

    icons = icons_by_type()
    canonical = icons.get(parsed.type)
    if canonical is None:
        errors.append(
            f"'{parsed.type}'은 알 수 없는 커밋 타입이다 — CONTRIBUTING.md의 타입 표를 따른다"
        )
        return Outcome(title=original, notes=notes, errors=errors)

    if parsed.icon is None:
        parsed = replace(parsed, icon=canonical)
        notes.append(f"{parsed.type} 타입의 이모지 {canonical}을 붙였다")
    elif parsed.icon != canonical:
        errors.append(
            f"이모지 {parsed.icon}이 {parsed.type} 타입과 맞지 않다 (기대: {canonical}) — "
            "이모지와 타입 중 무엇이 맞는지는 사람이 판단한다"
        )
        return Outcome(title=original, notes=notes, errors=errors)

    if parsed.scope is None or re.search(r"\s", parsed.scope):
        errors.append("scope는 필수다 — 변경 대상을 공백 없이 `type(scope): 제목`에 직접 적는다")

    return Outcome(title=parsed.render(), notes=notes, errors=errors)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR 제목을 커밋 제목 규칙으로 정규화한다")
    parser.add_argument("--title", required=True, help="검사할 PR 제목")
    args = parser.parse_args(argv)
    outcome = review(args.title)

    print(outcome.title)
    for note in outcome.notes:
        print(f"보정: {note}", file=sys.stderr)
    for error in outcome.errors:
        print(f"위반: {error}", file=sys.stderr)

    return 1 if outcome.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
