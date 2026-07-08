#!/usr/bin/env python3
"""Claude Code 세션 토큰·비용 트래커.

로컬 트랜스크립트(``~/.claude/projects/...``)를 파싱해 브랜치(=PR)별·모델별
토큰과 비용을 집계한다. LLM을 호출하지 않는 순수 파싱·산술 스크립트라
실행에 토큰이 들지 않는다.

용법::

    python scripts/token_report.py                 # 로컬 HTML 리포트 생성
    python scripts/token_report.py --comment       # 현재 브랜치 PR에 sticky 코멘트
    python scripts/token_report.py --comment --branch refactor/130-...
    python scripts/token_report.py --since 2026-07-01

집계 키는 세션이 아니라 메시지의 ``gitBranch``다. 한 PR에 세션이 여러 개면
같은 브랜치로 자동 합산되고, 한 세션이 여러 브랜치를 걸치면 메시지 단위로
쪼개진다. ``main`` 브랜치 작업은 어느 PR에도 안 붙는 "미분류" 버킷으로 모인다.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# 모델별 단가 (USD per 1M 토큰): (input, output)
PRICES: dict[str, tuple[float, float]] = {
    "fable": (10.0, 50.0),
    "opus": (5.0, 25.0),
    "sonnet": (3.0, 15.0),
    "haiku": (1.0, 5.0),
}

COMMENT_MARKER = "<!-- token-cost-tracker -->"
REPORT_DIR = ".reports"
REPORT_FILE = "token-report.html"


def rate_for(model: str) -> tuple[float, float]:
    """모델 id에서 단가를 찾는다. 알 수 없으면 Opus 단가로 보수적 처리."""
    for key, rate in PRICES.items():
        if key in model:
            return rate
    return PRICES["opus"]


def model_family(model: str) -> str:
    for key in PRICES:
        if key in model:
            return key
    return model or "unknown"


def cost_for(model: str, usage: dict) -> float:
    """usage 블록에서 실제 청구 비용(USD)을 계산한다.

    입력 정가 + 캐시 읽기 0.1배 + 캐시 쓰기(5m 1.25배, 1h 2배) + 출력 정가.
    """
    inr, outr = rate_for(model)
    creation = usage.get("cache_creation") or {}
    cache_5m = creation.get("ephemeral_5m_input_tokens", 0)
    cache_1h = creation.get("ephemeral_1h_input_tokens", 0)
    if not creation:
        # 세부 분해가 없으면 전체 캐시 쓰기를 5m로 간주
        cache_5m = usage.get("cache_creation_input_tokens", 0)
        cache_1h = 0
    inp = usage.get("input_tokens", 0)
    read = usage.get("cache_read_input_tokens", 0)
    out = usage.get("output_tokens", 0)
    dollars = (
        inp * inr + read * inr * 0.1 + cache_5m * inr * 1.25 + cache_1h * inr * 2.0 + out * outr
    ) / 1_000_000
    return dollars


def billed_tokens(usage: dict) -> int:
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("output_tokens", 0)
    )


@dataclass
class ModelStat:
    tokens: int = 0
    cost: float = 0.0
    sub_tokens: int = 0  # 서브에이전트(isSidechain) 분
    sub_cost: float = 0.0


@dataclass
class BranchStat:
    models: dict[str, ModelStat] = field(default_factory=dict)

    def add(self, family: str, tokens: int, cost: float, sidechain: bool) -> None:
        stat = self.models.setdefault(family, ModelStat())
        stat.tokens += tokens
        stat.cost += cost
        if sidechain:
            stat.sub_tokens += tokens
            stat.sub_cost += cost

    @property
    def total_cost(self) -> float:
        return sum(m.cost for m in self.models.values())

    @property
    def total_tokens(self) -> int:
        return sum(m.tokens for m in self.models.values())

    @property
    def sub_cost(self) -> float:
        return sum(m.sub_cost for m in self.models.values())


def transcript_dir(repo_root: Path) -> Path:
    """레포 경로로부터 Claude Code 트랜스크립트 디렉토리를 찾는다."""
    base = Path.home() / ".claude" / "projects"
    encoded = str(repo_root).replace("/", "-").replace(".", "-")
    exact = base / encoded
    if exact.is_dir():
        return exact
    # 폴백: 레포 basename으로 매칭
    matches = sorted(base.glob(f"*{repo_root.name}"))
    if matches:
        return matches[-1]
    raise FileNotFoundError(f"트랜스크립트 디렉토리를 찾을 수 없음: {exact}")


def iter_usage(directory: Path, since: datetime | None):
    """(branch, family, tokens, cost, sidechain)를 yield."""
    for path in directory.rglob("*.jsonl"):
        with path.open() as handle:
            for line in handle:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = obj.get("message")
                if not isinstance(message, dict):
                    continue
                usage = message.get("usage")
                if message.get("role") != "assistant" or not isinstance(usage, dict):
                    continue
                if since is not None:
                    ts = obj.get("timestamp", "")
                    if ts and ts[:10] < since.strftime("%Y-%m-%d"):
                        continue
                model = message.get("model") or "unknown"
                # Claude Code 합성 메시지(<synthetic>)는 실제 usage가 없어 제외
                if model.startswith("<"):
                    continue
                branch = obj.get("gitBranch") or "(unknown)"
                sidechain = bool(obj.get("isSidechain"))
                yield (
                    branch,
                    model_family(model),
                    billed_tokens(usage),
                    cost_for(model, usage),
                    sidechain,
                )


def aggregate(directory: Path, since: datetime | None) -> dict[str, BranchStat]:
    branches: dict[str, BranchStat] = {}
    for branch, family, tokens, cost, sidechain in iter_usage(directory, since):
        branches.setdefault(branch, BranchStat()).add(family, tokens, cost, sidechain)
    return branches


def branch_to_pr(branch: str) -> dict | None:
    """gh로 브랜치의 PR을 찾는다. 없으면 None."""
    if branch in ("main", "(unknown)"):
        return None
    try:
        out = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "all",
                "--json",
                "number,title,url",
                "--limit",
                "1",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    data = json.loads(out or "[]")
    return data[0] if data else None


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def fmt_cost(dollars: float) -> str:
    return f"${dollars:,.2f}"


# --------------------------------------------------------------------------- #
# HTML 리포트
# --------------------------------------------------------------------------- #

HTML_HEAD = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>토큰·비용 리포트</title><style>
:root{--bg:#f5f7fa;--surface:#fff;--surface2:#eef1f6;--ink:#19212e;
--muted:#5c6777;--faint:#8a94a3;--border:#e0e5ec;--accent:#3d5a80;
--sonnet:#d98a3d;--good:#3f9163;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",sans-serif;}
@media(prefers-color-scheme:dark){:root{--bg:#10141b;--surface:#1a2029;
--surface2:#222a35;--ink:#e7ebf2;--muted:#9aa5b3;--faint:#6b7683;
--border:#29313d;--accent:#7fa3cc;--sonnet:#e0a05a;--good:#5cb585;}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:var(--sans);line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto;padding:40px 24px 72px}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
h1{font-size:24px;margin:0 0 6px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:14px;margin:0 0 28px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:30px}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:12px;
padding:16px 18px}.stat .l{font-size:12.5px;color:var(--muted);margin-bottom:8px}
.stat .b{font-size:25px;font-weight:650;letter-spacing:-.02em}
.stat .b small{font-size:14px;color:var(--muted);font-weight:500}
h2{font-size:15px;margin:26px 0 12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;
overflow:hidden}.scroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:520px}
th,td{text-align:right;padding:10px 12px;border-bottom:1px solid var(--border)}
th:first-child,td:first-child{text-align:left}
thead th{color:var(--faint);font-weight:600;font-size:11.5px;letter-spacing:.03em;
text-transform:uppercase}tbody tr:last-child td{border-bottom:none}
.pr{font-family:var(--mono);color:var(--accent)}.desc{color:var(--muted)}
td.c{font-family:var(--mono)}.tag{font-size:11px;color:var(--faint)}
.deleg{color:var(--sonnet);font-family:var(--mono)}
tfoot td{font-weight:600;border-top:2px solid var(--border)}
.foot{color:var(--faint);font-size:12px;margin-top:22px}
.mono-legend span{margin-right:14px;font-size:12px;color:var(--muted)}
</style></head><body><div class="wrap">"""

HTML_TAIL = "</div></body></html>"


def render_html(branches: dict[str, BranchStat], generated: str) -> str:
    ranked = sorted(branches.items(), key=lambda kv: kv[1].total_cost, reverse=True)
    total_cost = sum(b.total_cost for b in branches.values())
    total_tokens = sum(b.total_tokens for b in branches.values())
    total_sub = sum(b.sub_cost for b in branches.values())
    fam_totals: dict[str, float] = {}
    for stat in branches.values():
        for fam, ms in stat.models.items():
            fam_totals[fam] = fam_totals.get(fam, 0.0) + ms.cost

    parts = [HTML_HEAD]
    parts.append("<h1>토큰·비용 리포트</h1>")
    parts.append(
        f'<p class="sub">생성: {generated} · 집계 키: gitBranch(=PR) · 로컬 트랜스크립트 실측</p>'
    )

    parts.append('<div class="stats">')
    parts.append(
        f'<div class="stat"><div class="l">총 비용</div>'
        f'<div class="b num">{fmt_cost(total_cost)}</div></div>'
    )
    parts.append(
        f'<div class="stat"><div class="l">총 토큰</div>'
        f'<div class="b num">{fmt_tokens(total_tokens)}</div></div>'
    )
    sub_pct = (total_sub / total_cost * 100) if total_cost else 0
    parts.append(
        f'<div class="stat"><div class="l">서브에이전트 위임분</div>'
        f'<div class="b num">{fmt_cost(total_sub)} '
        f"<small>{sub_pct:.0f}%</small></div></div>"
    )
    parts.append("</div>")

    parts.append("<h2>PR·브랜치별 비용</h2>")
    parts.append(
        '<div class="card scroll"><table><thead><tr>'
        "<th>브랜치 / PR</th><th>모델</th><th>토큰</th>"
        "<th>위임(sub)</th><th>비용</th></tr></thead><tbody>"
    )
    for branch, stat in ranked:
        pr = branch_to_pr(branch)
        if branch == "main":
            label = '<span class="desc">main · 미분류</span>'
        elif pr:
            label = (
                f'<span class="pr">#{pr["number"]}</span> '
                f'<span class="desc">{esc(pr["title"])}</span>'
            )
        else:
            label = f'<span class="desc">{esc(branch)}</span>'
        fams = " · ".join(sorted(stat.models))
        sub = stat.sub_cost
        sub_cell = fmt_cost(sub) if sub else "—"
        parts.append(
            f"<tr><td>{label}</td>"
            f'<td class="tag">{esc(fams)}</td>'
            f'<td class="num">{fmt_tokens(stat.total_tokens)}</td>'
            f'<td class="deleg">{sub_cell}</td>'
            f'<td class="c">{fmt_cost(stat.total_cost)}</td></tr>'
        )
    parts.append(
        f"<tfoot><tr><td>합계</td><td></td>"
        f'<td class="num">{fmt_tokens(total_tokens)}</td>'
        f'<td class="deleg">{fmt_cost(total_sub)}</td>'
        f'<td class="c">{fmt_cost(total_cost)}</td></tr></tfoot>'
    )
    parts.append("</tbody></table></div>")

    parts.append("<h2>모델별 비용</h2>")
    parts.append(
        '<div class="card scroll"><table><thead><tr>'
        "<th>모델</th><th>단가 (in/out per 1M)</th><th>비용</th>"
        "</tr></thead><tbody>"
    )
    for fam in sorted(fam_totals, key=lambda k: fam_totals[k], reverse=True):
        inr, outr = PRICES.get(fam, (0, 0))
        parts.append(
            f"<tr><td>{esc(fam)}</td>"
            f'<td class="tag">${inr:g} / ${outr:g}</td>'
            f'<td class="c">{fmt_cost(fam_totals[fam])}</td></tr>'
        )
    parts.append("</tbody></table></div>")

    parts.append(
        '<p class="foot">비용은 입력 정가 + 캐시 읽기 0.1배 + 캐시 쓰기'
        "(5m 1.25배 / 1h 2배) + 출력 정가로 산출. 서브에이전트 위임분은 "
        "isSidechain 메시지 기준. main 버킷은 어느 PR에도 안 붙은 작업.</p>"
    )
    parts.append(HTML_TAIL)
    return "".join(parts)


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --------------------------------------------------------------------------- #
# PR sticky 코멘트
# --------------------------------------------------------------------------- #


def render_comment(branch: str, stat: BranchStat, pr: dict) -> str:
    lines = [
        COMMENT_MARKER,
        f"### 💰 Claude Code 비용 — `{branch}`",
        "",
        "| 모델 | 토큰 | 비용 |",
        "| --- | ---: | ---: |",
    ]
    for fam in sorted(stat.models, key=lambda k: stat.models[k].cost, reverse=True):
        ms = stat.models[fam]
        note = " (위임)" if ms.sub_cost else ""
        lines.append(f"| {fam}{note} | {fmt_tokens(ms.tokens)} | {fmt_cost(ms.cost)} |")
    lines.append(
        f"| **합계** | **{fmt_tokens(stat.total_tokens)}** | **{fmt_cost(stat.total_cost)}** |"
    )
    if stat.sub_cost:
        lines.append("")
        lines.append(f"서브에이전트 위임분: {fmt_cost(stat.sub_cost)}")
    lines.append("")
    lines.append(
        "<sub>로컬 트랜스크립트 실측 · 콜드스타트 오버헤드 포함 · PR당 브랜치 기준 누적 갱신</sub>"
    )
    return "\n".join(lines)


def repo_slug() -> str:
    out = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return out


def find_sticky_comment(slug: str, pr_number: int) -> int | None:
    out = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            f"repos/{slug}/issues/{pr_number}/comments",
            "-q",
            f'.[] | select(.body | contains("{COMMENT_MARKER}")) | .id',
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not out:
        return None
    return int(out.splitlines()[0])


def post_comment(slug: str, pr_number: int, body: str) -> None:
    tmp = Path(REPORT_DIR) / ".comment-body.md"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(body)
    existing = find_sticky_comment(slug, pr_number)
    if existing is not None:
        subprocess.run(
            [
                "gh",
                "api",
                "--method",
                "PATCH",
                f"repos/{slug}/issues/comments/{existing}",
                "-F",
                f"body=@{tmp}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"코멘트 갱신됨 (#{pr_number}, comment {existing})")
    else:
        subprocess.run(
            ["gh", "api", f"repos/{slug}/issues/{pr_number}/comments", "-F", f"body=@{tmp}"],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"코멘트 생성됨 (#{pr_number})")
    tmp.unlink(missing_ok=True)


def current_branch(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def repo_toplevel() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return Path(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude Code 토큰·비용 트래커")
    parser.add_argument(
        "--comment", action="store_true", help="현재(또는 --branch) PR에 sticky 코멘트"
    )
    parser.add_argument("--branch", help="코멘트 대상 브랜치 (기본: 현재 브랜치)")
    parser.add_argument("--since", help="이 날짜 이후만 집계 (YYYY-MM-DD)")
    args = parser.parse_args()

    since = datetime.strptime(args.since, "%Y-%m-%d") if args.since else None
    repo_root = repo_toplevel()
    directory = transcript_dir(repo_root)
    branches = aggregate(directory, since)

    if not branches:
        print("집계할 usage 데이터가 없음.")
        return 0

    if args.comment:
        branch = args.branch or current_branch(repo_root)
        stat = branches.get(branch)
        if stat is None:
            print(f"'{branch}' 브랜치의 usage 데이터가 없음.")
            return 1
        pr = branch_to_pr(branch)
        if pr is None:
            print(f"'{branch}'에 연결된 PR을 찾을 수 없음.")
            return 1
        slug = repo_slug()
        post_comment(slug, pr["number"], render_comment(branch, stat, pr))
        return 0

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = render_html(branches, generated)
    out_path = repo_root / REPORT_DIR / REPORT_FILE
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    total = sum(b.total_cost for b in branches.values())
    print(f"리포트 생성: {out_path}")
    print(f"브랜치 {len(branches)}개 · 총 {fmt_cost(total)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
