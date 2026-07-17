# 에이전트 작업 규칙

## 응답 언어 (최우선)

사용자와의 모든 대화, 문서 작성, 계획서, 태스크 목록은 예외 없이 **한국어**로 작성합니다.

## 문서 줄바꿈

마크다운 문서는 **100칼럼 이내에서 문장·절 경계로 hard wrap**합니다.
Issue·PR 본문은 줄바꿈하지 않습니다(no wrap).
surface별 전체 정책과 근거는 [CONTRIBUTING.md](CONTRIBUTING.md#줄바꿈-정책) 참조.

## 이슈 기반 작업 시작

사용자가 이슈 번호를 선언하면 바로 구현 계획을 작성하지 말고,
먼저 구현 범위·설계 의도·접근 방식에 대해 질문하여 합의한 후 계획을 수립합니다.

## 브랜치 규칙

브랜치 생성 전 **반드시 원격 main을 동기화**한 뒤 생성합니다.
명명 규칙과 동기화 명령은 [CONTRIBUTING.md](CONTRIBUTING.md#브랜치-명명-규칙)를 참조합니다.

## Python 실행 환경

- **시스템 파이썬 사용 금지.** 항상 프로젝트 `.venv`를 활성화한 뒤 작업합니다.

  ```bash
  source .venv/bin/activate
  ```

- 활성화 후에는 `ruff`, `pytest`, `pre-commit` 등을 접두사 없이 그대로 실행합니다.
- `uv run` 사용 금지. 패키지 추가는 `uv add [package]`.
- Python 버전: 3.12 이상.
- 커밋 전 `ruff check`, `ruff format`, `pytest` 통과 필수 (pre-commit 훅이 강제).

> 에이전트 참고: Bash 도구는 호출마다 새 셸이라 `activate` 상태가 유지되지 않습니다.
> 한 호출로 끝내려면 `source .venv/bin/activate && pytest`처럼 묶거나
> `.venv/bin/pytest`를 직접 호출하세요.

## Python 코딩 스타일

- 메서드·속성에 `_` 접두사를 붙이지 않습니다. 기존 코드베이스 전체가 이 스타일로 작성되어 있습니다.
- 진짜 이름 숨김이 필요한 경우에만 `__` (네임 맹글링)을 사용합니다.

## 커밋 및 PR

커밋·PR 생성 전 반드시 [CONTRIBUTING.md](CONTRIBUTING.md)를 읽고 규칙을 따릅니다.
