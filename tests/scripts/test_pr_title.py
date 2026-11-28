import re
from pathlib import Path

import pytest
from pr_title import icons_by_type, main, parse, review

CONTRIBUTING = Path(__file__).parents[2] / "CONTRIBUTING.md"

# CONTRIBUTING.md 타입 표의 한 행: | ✨ | `feat` | 새로운 기능 추가 |
CONTRIBUTING_ROW = re.compile(r"^\|\s*(?P<icon>\S+)\s*\|\s*`(?P<type>[a-z-]+)`\s*\|")

BRANCH_COMMITS = (
    "✨ feat(data): 지수 유니버스 산출 경로 추가",
    "✅ test(data): 지수 구성종목 e2e 테스트 추가",
    "📝 docs(architecture): 데이터 모델에 유니버스 산출 경로 반영",
)


def test_missing_gitmoji_is_derived_from_type() -> None:
    outcome = review("feat(data): 지수 구성종목 조회 경로 추가")

    assert outcome.title == "✨ feat(data): 지수 구성종목 조회 경로 추가"
    assert outcome.errors == []
    assert outcome.notes


def test_compliant_title_is_left_untouched() -> None:
    title = "🧹 chore(data): pykrx 최신화"

    outcome = review(title)

    assert outcome.title == title
    assert outcome.notes == []
    assert outcome.errors == []


def test_breaking_change_marker_is_preserved() -> None:
    outcome = review("refactor(ports)!: SignalModel 계약 변경")

    assert outcome.title == "♻️ refactor(ports)!: SignalModel 계약 변경"


def test_gitmoji_conflicting_with_type_is_left_to_the_author() -> None:
    title = "🐛 feat(cli): collect --index 옵션 추가"

    outcome = review(title)

    assert outcome.title == title
    assert len(outcome.errors) == 1
    assert "맞지 않다" in outcome.errors[0]


def test_unknown_type_is_reported_as_violation() -> None:
    outcome = review("improve(cli): 옵션 정리")

    assert outcome.errors
    assert "알 수 없는 커밋 타입" in outcome.errors[0]


def test_title_outside_commit_format_is_reported_as_violation() -> None:
    outcome = review("유니버스 관리 개선")

    assert outcome.title == "유니버스 관리 개선"
    assert outcome.errors


def test_trailing_pr_number_is_stripped() -> None:
    outcome = review("✨ feat(data): 지수 유니버스 산출 경로 추가 (#38)")

    assert outcome.title == "✨ feat(data): 지수 유니버스 산출 경로 추가"
    assert any("(#N)" in note for note in outcome.notes)


def test_scope_is_filled_when_branch_commits_agree() -> None:
    outcome = review("feat: 지수 유니버스 산출 경로 추가", commit_titles=BRANCH_COMMITS)

    assert outcome.title == "✨ feat(data): 지수 유니버스 산출 경로 추가"


def test_majority_scope_is_filled() -> None:
    commits = (
        *BRANCH_COMMITS,
        "✨ feat(data): pykrx 지수 구성종목 소스 어댑터 추가",
        "✨ feat(cli): collect --index 옵션 추가",
    )

    outcome = review("feat: 지수 유니버스 산출 경로 추가", commit_titles=commits)

    assert outcome.title == "✨ feat(data): 지수 유니버스 산출 경로 추가"
    assert any("다수 scope" in note for note in outcome.notes)


def test_tied_scope_candidates_are_reported_but_not_filled() -> None:
    commits = (*BRANCH_COMMITS, "✨ feat(cli): collect --index 옵션 추가")

    outcome = review("feat: 지수 유니버스 산출 경로 추가", commit_titles=commits)

    assert outcome.title == "✨ feat: 지수 유니버스 산출 경로 추가"
    assert any("동수" in note for note in outcome.notes)
    assert outcome.errors == []


def test_copying_the_linked_issue_title_is_a_violation() -> None:
    outcome = review(
        "✨ feat: 유니버스 관리 — 지수 구성종목(KOSPI 200) 조회",
        issue_title="feat: 유니버스 관리 — 지수 구성종목(KOSPI 200) 조회",
    )

    assert outcome.errors
    assert "이슈 제목과 같다" in outcome.errors[0]


def test_summary_differing_from_the_issue_title_passes() -> None:
    outcome = review(
        "✨ feat(data): 지수 구성종목 유니버스 조회 경로 추가",
        issue_title="feat: 유니버스 관리 — 지수 구성종목(KOSPI 200) 조회",
    )

    assert outcome.errors == []


@pytest.mark.parametrize(
    "title",
    ["✨feat: x", ": x", "feat:", "Feat: x", "유니버스 관리 개선", "WIP"],
)
def test_malformed_titles_do_not_parse(title: str) -> None:
    assert parse(title) is None


def test_contributing_table_matches_the_gitmoji_mapping() -> None:
    icons = icons_by_type()
    rows = [
        match.groupdict()
        for line in CONTRIBUTING.read_text(encoding="utf-8").splitlines()
        if (match := CONTRIBUTING_ROW.match(line)) is not None
    ]

    assert rows, "CONTRIBUTING.md에서 타입 표를 찾지 못했다"
    mismatched = {
        row["type"]: (row["icon"], icons.get(row["type"]))
        for row in rows
        if icons.get(row["type"]) != row["icon"]
    }
    assert mismatched == {}, "CONTRIBUTING.md 표와 cz-conventional-gitmoji 매핑이 어긋났다"


def test_cli_prints_normalized_title_and_signals_violations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--title", "feat(data): 지수 유니버스 산출 경로 추가"]) == 0
    assert capsys.readouterr().out.strip() == "✨ feat(data): 지수 유니버스 산출 경로 추가"

    assert main(["--title", "유니버스 관리 개선"]) == 1


def test_cli_infers_scope_from_commit_titles_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commits_file = tmp_path / "commit-titles.txt"
    commits_file.write_text("\n".join(BRANCH_COMMITS), encoding="utf-8")

    exit_code = main(
        ["--title", "feat: 지수 유니버스 산출 경로 추가", "--commits-file", str(commits_file)]
    )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "✨ feat(data): 지수 유니버스 산출 경로 추가"
