"""PR 제목을 커밋 제목 규칙(`<emoji> <type>(<scope>): <subject>`)으로 정규화한다.

이 레포는 squash 머지만 허용하므로 머지 커밋 제목이 PR 제목을 그대로 물려받는다.
PR 제목에 gitmoji가 빠진 채 main에 남지 않도록
타입에서 결정론적으로 도출되는 부분은 CI가 채우고, 사람이 판단해야 하는 위반만 실패로 알린다.

이모지-타입 매핑의 SoT는 commit-msg 훅이 쓰는 cz-conventional-gitmoji 테이블이다.
"""

import argparse
import re
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from shared.utils import get_gitmojis

TITLE_PATTERN = re.compile(
    r"""
    ^
    (?:(?P<icon>[^\w\s]\S*)[ ]+)?   # gitmoji — 없으면 타입에서 도출해 채운다
    (?P<type>[a-z][a-z-]*)          # 커밋 타입
    (?:\((?P<scope>[^()]+)\))?      # scope — 생략 가능
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


def infer_scope(commit_type: str, commit_titles: Sequence[str]) -> tuple[str | None, str | None]:
    """브랜치의 같은 타입 커밋에서 scope를 추론한다. 동수로 갈리면 채우지 않고 후보만 알린다."""
    scopes: list[str] = []
    for commit_title in commit_titles:
        parsed = parse(commit_title)
        if parsed is not None and parsed.type == commit_type and parsed.scope is not None:
            scopes.append(parsed.scope)

    counts = Counter(scopes)
    ranked = counts.most_common()
    if not ranked:
        return None, None

    candidates = ", ".join(sorted(counts))
    if len(ranked) == 1:
        scope = ranked[0][0]
        return scope, f"브랜치의 {commit_type} 커밋이 모두 ({scope}) scope라 제목에 반영했다"

    (top_scope, top_count), (_, runner_up_count) = ranked[0], ranked[1]
    if top_count > runner_up_count:
        return top_scope, (
            f"브랜치 {commit_type} 커밋의 다수 scope인 ({top_scope})를 반영했다 "
            f"(후보: {candidates})"
        )
    return None, f"scope 후보가 동수라 자동 반영하지 않았다 (후보: {candidates})"


def _flatten(text: str) -> str:
    return " ".join(text.split()).casefold()


def _copies_issue_title(subject: str, issue_title: str) -> bool:
    parsed = parse(issue_title)
    issue_subject = parsed.subject if parsed is not None else issue_title
    return _flatten(subject) == _flatten(issue_subject)


def review(
    title: str,
    *,
    commit_titles: Sequence[str] = (),
    issue_title: str | None = None,
) -> Outcome:
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

    if parsed.scope is None:
        scope, note = infer_scope(parsed.type, commit_titles)
        if scope is not None:
            parsed = replace(parsed, scope=scope)
        if note is not None:
            notes.append(note)

    if issue_title is not None and _copies_issue_title(parsed.subject, issue_title):
        errors.append(
            "제목이 연결된 이슈 제목과 같다 — 이슈는 '무엇이 필요한가', "
            "커밋은 '무엇을 바꿨는가'를 쓴다"
        )

    return Outcome(title=parsed.render(), notes=notes, errors=errors)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR 제목을 커밋 제목 규칙으로 정규화한다")
    parser.add_argument("--title", required=True, help="검사할 PR 제목")
    parser.add_argument(
        "--commits-file",
        type=Path,
        help="브랜치 커밋 제목 목록 파일 (한 줄에 하나) — scope 추론에 쓴다",
    )
    parser.add_argument("--issue-title", help="PR이 닫는 이슈의 제목 — 복사 여부를 검사한다")
    args = parser.parse_args(argv)

    commit_titles: list[str] = []
    if args.commits_file is not None:
        commits_file: Path = args.commits_file
        commit_titles = commits_file.read_text(encoding="utf-8").splitlines()

    outcome = review(
        args.title,
        commit_titles=commit_titles,
        issue_title=args.issue_title,
    )

    print(outcome.title)
    for note in outcome.notes:
        print(f"보정: {note}", file=sys.stderr)
    for error in outcome.errors:
        print(f"위반: {error}", file=sys.stderr)

    return 1 if outcome.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
