# Claude Code 프로젝트 규칙

## 응답 언어 (최우선)

사용자와의 모든 대화, 문서 작성, 계획서, 태스크 목록은 예외 없이 **한국어**로 작성합니다.

## Python 실행 환경

- 패키지 추가: `uv add [package]`
- 스크립트/도구 실행: **반드시 `.venv/bin/` 바이너리를 직접 호출** (`uv run` 사용 금지)
  - 예: `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/pre-commit`
- Python 버전: 3.12 이상

## Git 커밋 규칙

형식: `<emoji> <type>(<scope>): <subject>`

- 이모지는 유니코드 직접 사용 (`:sparkles:` 같은 콜론 코드 금지)
- subject는 한국어, 명령조, 끝에 온점 금지
- 이슈 번호는 **Footer에만** (`Closes #N` 또는 `Ref #N`, 둘 중 하나만)
- 제목 끝에 `(#N)` 형태 이슈 번호 금지

| 이모지 | 타입 |
|--------|------|
| ✨ | feat |
| 🐛 | fix |
| ♻️ | refactor |
| 📝 | docs |
| ✅ | test |
| 🔧 | config |
| 🧹 | chore |
| 🚧 | wip |
| 🚀 | deploy |
| 🎉 | init |
| ⚡️ | perf |
| 🔥 | dump |
| 🎨 | style |

본문(Body): what/why 중심, 한 줄 72자 이하, `- ` 글머리 기호, 명사형 종결 (어색하면 음슴체 허용)

Footer: 이슈 종료는 `Closes #N`, 참조는 `Ref #N`, 같은 이슈에 중복 금지, 다중 이슈는 `Closes #17, #18` 또는 별도 라인

커밋 전 검사: `.venv/bin/pre-commit run --all-files`

## 브랜치 규칙

형식: `<type>/<issue-number>-<description>` (예: `feat/12-add-boiler`)

**브랜치 생성 전 반드시 원격 main 동기화:**

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b <branch-name>
```

## 이슈 기반 작업 시작

사용자가 이슈 번호를 선언하면 바로 구현 계획을 작성하지 말고, 먼저 구현 범위·설계 의도·접근 방식에 대해 질문하여 합의한 후 계획을 수립합니다.

## PR 작성

- `.github/PULL_REQUEST_TEMPLATE.md` 템플릿 준수
- PR 제목 형식: 커밋 메시지 제목과 동일 (`<emoji> <type>(<scope>): <subject>`)
- `.gitignore` 대상 파일(`.cursor/`, `.cursorrules/`, `.vscode/`, `.env` 등)은 커밋 메시지·PR 어디에도 언급하지 않습니다

## GitHub Actions (@claude 에이전트)

`@claude` 멘션으로 GitHub Actions에서 코드를 작성·수정할 때 커밋 전 아래 순서를 반드시 실행합니다:

1. `.venv/bin/pre-commit run --all-files` — 오류 발생 시 수정 후 재실행
2. `.venv/bin/pytest` — 모두 통과한 상태에서만 커밋
3. PR 제목은 커밋 메시지 제목과 동일하게 `<emoji> <type>(<scope>): <subject>` 형식 준수 (이슈 번호 제목에 포함 금지)
