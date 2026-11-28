import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).parents[2] / ".github/workflows/pr-title.yml"


@pytest.mark.parametrize(
    ("can_edit", "title", "expected_status", "edited_title"),
    [
        ("true", "docs(templates): 양식 정리", 0, "📝 docs(templates): 양식 정리"),
        ("false", "docs(templates): 양식 정리", 1, None),
        ("false", "📝 docs(templates): 양식 정리", 0, None),
        ("true", "🐛 docs(templates): 양식 정리", 1, None),
        ("true", "📝 docs: 양식 정리", 1, None),
        ("false", "📝 docs: 양식 정리", 1, None),
        ("true", "📝 docs( ): 양식 정리", 1, None),
        ("true", "📝 docs(templates): 양식 정리 (#123)", 0, "📝 docs(templates): 양식 정리"),
    ],
)
def test_workflow_checks_title_format_and_only_writes_when_allowed(
    can_edit: str,
    title: str,
    expected_status: int,
    edited_title: str | None,
    tmp_path: Path,
) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    step = next(
        step
        for step in workflow["jobs"]["normalize"]["steps"]
        if step.get("name") == "Normalize + lint"
    )
    # 실제 워크플로와 제목 CLI를 실행하고 uv 실행 및 GitHub 쓰기만 대체한다.
    stub = """uv() {
    shift 2
    "$PYTHON_EXECUTABLE" "$REPOSITORY_ROOT/$1" "${@:2}"
}
gh() {
    printf '%s\\n' "$*" >> gh-args.txt
}
"""
    summary_file = tmp_path / "summary.md"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", stub + step["run"]],
        cwd=tmp_path,
        env={
            "PATH": os.environ["PATH"],
            "PYTHON_EXECUTABLE": sys.executable,
            "REPOSITORY_ROOT": str(WORKFLOW.parents[2]),
            "GITHUB_STEP_SUMMARY": str(summary_file),
            "CAN_EDIT_TITLE": can_edit,
            "PR_TITLE": title,
            "PR_NUMBER": "42",
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == expected_status, result.stderr
    args_file = tmp_path / "gh-args.txt"
    if edited_title is None:
        assert not args_file.exists()
    else:
        assert args_file.read_text().strip() == f"pr edit 42 --title {edited_title}"
    if "docs:" in title or "docs( )" in title:
        assert "scope" in summary_file.read_text()
    if can_edit == "false" and title == "docs(templates): 양식 정리":
        assert "직접 수정" in summary_file.read_text()
        assert "📝 docs(templates): 양식 정리" in summary_file.read_text()
