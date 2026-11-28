import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).parents[2] / ".github/workflows/pr-title.yml"


@pytest.mark.parametrize(
    ("body", "issue_number"),
    [
        ("Closes #123", "123"),
        ("Ref #123", "123"),
        ("Refs #123", "123"),
        ("refs #456", "456"),
        ("## Related issues\n\nRefs #123\nCloses #456", "123"),
        ("## Summary\n\n이슈 없이 진행합니다.", None),
        ("Refs #N", None),
        ("Closes #123, #456", "123"),
        ("```markdown\n## Related issues\nRefs #999999\n```\nCloses #123", "123"),
        ("## Summary\n\n예시: `Refs #999999`\n\n## Related issues\n\nCloses #123", "123"),
        ("Refs #999999\n\n## Related issues\n\n- Ref #123", "123"),
        ("## Related issues\n\n<!-- Refs #999999 -->\nRefs #123", "123"),
        ("## Related issues\n\n<!--\nRefs #999999\n-->\nRefs #123", "123"),
        ("## Related issues\n\n```text\nRefs #999999\n```\nRefs #123", "123"),
        ("## Related issues\n\n~~~\nRefs #999999\n~~~\nRefs #123", "123"),
        ("## Related issues\n\n`Refs #999999`\n    Refs #999998\nRefs #123", "123"),
        ("## Related issues\n\n연결 없음\n\n## Test Plan\n\nRefs #999999", None),
        ("설명에서 Refs #999999 문법을 소개합니다.", None),
    ],
)
def test_workflow_looks_up_the_first_referenced_issue(
    body: str, issue_number: str | None, tmp_path: Path
) -> None:
    result = _run_step(
        "Look up linked issue title",
        tmp_path,
        "gh() { printf '%s\\n' \"$*\" > gh-args.txt; printf '%s\\n' 'feat: 연결된 이슈'; }\n",
        {"PR_BODY": body},
    )
    assert result.returncode == 0, result.stderr

    title_file = tmp_path / "issue-title.txt"
    args_file = tmp_path / "gh-args.txt"
    if issue_number is None:
        assert not args_file.exists()
        assert not title_file.exists()
    else:
        assert (
            args_file.read_text().strip() == f"issue view {issue_number} --json title --jq .title"
        )
        assert title_file.read_text().strip() == "feat: 연결된 이슈"


def _run_step(
    name: str, tmp_path: Path, stub: str, extra_env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    step = next(step for step in workflow["jobs"]["normalize"]["steps"] if step.get("name") == name)
    return subprocess.run(
        [
            "bash",
            "-e",
            "-o",
            "pipefail",
            "-c",
            'uv() { shift 2; "$PYTHON_EXECUTABLE" "$REPOSITORY_ROOT/$1" "${@:2}"; }\n'
            + stub
            + step["run"],
        ],
        cwd=tmp_path,
        env={
            "PATH": os.environ["PATH"],
            "PYTHON_EXECUTABLE": sys.executable,
            "REPOSITORY_ROOT": str(WORKFLOW.parents[2]),
            "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
            **extra_env,
        },
        capture_output=True,
        text=True,
    )


def test_issue_lookup_failure_blocks_the_check_and_removes_partial_title(tmp_path: Path) -> None:
    result = _run_step(
        "Look up linked issue title",
        tmp_path,
        "gh() { printf '%s\\n' '부분 응답'; return 1; }\n",
        {"PR_BODY": "Refs #123"},
    )

    assert result.returncode != 0
    assert not (tmp_path / "issue-title.txt").exists()
    assert "조회" in (tmp_path / "summary.md").read_text()


def test_workflow_requests_issue_read_permission() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))

    assert workflow["permissions"]["issues"] == "read"


@pytest.mark.parametrize(
    ("can_edit", "title", "expected_status", "should_edit"),
    [
        ("true", "feat: 조회 경로 추가", 0, True),
        ("false", "feat: 조회 경로 추가", 1, False),
        ("false", "✨ feat: 조회 경로 추가", 0, False),
        ("false", "🐛 feat: 조회 경로 추가", 1, False),
    ],
)
def test_read_only_runs_report_required_edits_without_writing_or_requiring_optional_scope(
    can_edit: str,
    title: str,
    expected_status: int,
    should_edit: bool,
    tmp_path: Path,
) -> None:
    (tmp_path / "commit-titles.txt").write_text("✨ feat(data): 조회 경로 추가\n")
    stub = """gh() {
    printf '%s\\n' "$*" > gh-args.txt
}
"""
    result = _run_step(
        "Normalize + lint",
        tmp_path,
        stub,
        {
            "CAN_EDIT_TITLE": can_edit,
            "PR_TITLE": title,
            "PR_NUMBER": "42",
        },
    )

    assert result.returncode == expected_status, result.stderr
    args_file = tmp_path / "gh-args.txt"
    if should_edit:
        assert args_file.read_text().strip() == "pr edit 42 --title ✨ feat(data): 조회 경로 추가"
    else:
        assert not args_file.exists()
    if can_edit == "false" and title == "feat: 조회 경로 추가":
        summary = (tmp_path / "summary.md").read_text()
        assert "직접" in summary
        assert "✨ feat: 조회 경로 추가" in summary
