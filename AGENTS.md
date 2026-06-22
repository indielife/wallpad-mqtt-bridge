# Claude Code 프로젝트 규칙

## 응답 언어 (최우선)

사용자와의 모든 대화, 문서 작성, 계획서, 태스크 목록은 예외 없이 **한국어**로 작성합니다.

## 이슈 기반 작업 시작

사용자가 이슈 번호를 선언하면 바로 구현 계획을 작성하지 말고, 먼저 구현 범위·설계 의도·접근 방식에 대해 질문하여 합의한 후 계획을 수립합니다.

## 브랜치 규칙

명명 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md) 참조. 브랜치 생성 전 반드시 원격 main 동기화:

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b <branch-name>
```

## Python 실행 환경

- 패키지 추가: `uv add [package]`
- 스크립트/도구 실행: **반드시 `.venv/bin/` 바이너리를 직접 호출** (`uv run` 사용 금지)
  - 예: `.venv/bin/pytest`, `.venv/bin/pre-commit`
- Python 버전: 3.12 이상
- 린트/포맷: `.venv/bin/ruff check` 및 `.venv/bin/ruff format` 통과 필수

## 커밋 및 PR

커밋·PR 생성 전 반드시 [CONTRIBUTING.md](CONTRIBUTING.md)를 읽고 규칙을 따릅니다.
