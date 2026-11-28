import os
import subprocess
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
    ],
)
def test_workflow_looks_up_the_first_referenced_issue(
    body: str, issue_number: str | None, tmp_path: Path
) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    lookup = next(
        step
        for step in workflow["jobs"]["normalize"]["steps"]
        if step.get("name") == "Look up linked issue title"
    )
    # 실제 조회 단계는 그대로 실행하고 gh만 대체해 외부 호출 없이 전달 인자를 검증한다.
    stub = """gh() {
    printf '%s\\n' "$*" > gh-args.txt
    printf '%s\\n' 'feat: 연결된 이슈'
}
"""
    subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", stub + lookup["run"]],
        cwd=tmp_path,
        env={"PATH": os.environ["PATH"], "PR_BODY": body},
        check=True,
        capture_output=True,
        text=True,
    )

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
