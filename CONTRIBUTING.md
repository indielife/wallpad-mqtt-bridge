# Git 커밋 메시지 규칙 (Gitmoji + Conventional Commits)

## 1. 커밋 메시지 구조

```text
<emoji> <type>(<scope>): <subject>

<body>

<footer>
```

## 2. 제목(Subject) 규칙

- **형식:** `<emoji> <type>(<scope>): <subject>`
- **이모지:** 유니코드 직접 사용 — 콜론 코드(`:sparkles:`) 사용 금지
- **scope:** 변경 대상 모듈 또는 파일명 기준, 생략 가능
- **길이:** 영문 기준 50자 이하
- **subject:** 한국어, 명령조(예: `~ 추가`, `~ 수정`), 끝에 온점 금지

### 타입 및 이모지 참조표

| 이모지 | 타입 | 용도 |
|--------|------|------|
| ✨ | `feat` | 새로운 기능 추가 |
| 🐛 | `fix` | 버그 수정 |
| 📝 | `docs` | 문서 수정 |
| ♻️ | `refactor` | 코드 리팩토링 (기능 변화 없음) |
| ✅ | `test` | 테스트 코드 추가 및 수정 |
| 🔧 | `config` | 설정 변경, 패키지 관리 |
| 🧹 | `chore` | 기타 변경사항 |
| 🚀 | `deploy` | 배포 관련 |
| 🎉 | `init` | 프로젝트 초기화 |
| ⚡️ | `perf` | 성능 개선 |
| 🔥 | `dump` | 코드 또는 파일 삭제 |
| 🎨 | `style` | 스타일 및 포맷팅 |
| 🚧 | `wip` | 작업 중 (WIP) |

### 올바른 예시

```
✨ feat(pipeline): KPI 배치 정규화 단계 추가
🐛 fix(model): PM 지표 누락 엣지 케이스 처리
♻️ refactor(etl): pandas groupby를 polars로 교체
🔧 config(pre-commit): commitizen 훅 설정 추가
```

### 잘못된 예시

```
# ❌ 이모지 누락
feat: 로그인 기능 추가

# ❌ 콜론 코드 사용
:sparkles: feat: 새 기능 추가

# ❌ 제목에 이슈 번호 포함
🔧 config: config.yaml 마이그레이션 (#67)
```

## 3. 본문(Body) 규칙

- 한 줄 72자 이하
- `what` / `why` 중심, 구현 방법(`how`)은 지양
- 글머리 기호(`- `) 사용, 명사형 종결 — 어색할 경우 음슴체(`~함`, `~음`) 허용

## 4. 바닥글(Footer) 규칙

- 이슈 종료: `Closes #<번호>` / 이슈 참조: `Ref #<번호>`
- 동일 이슈에 `Closes`와 `Ref` 중복 금지
- 여러 이슈: `Closes #17, #18` 또는 별도 라인

## 5. 커밋 전 검사

```bash
.venv/bin/pre-commit run --all-files
```

## 6. 브랜치 명명 규칙

형식: `<type>/<issue-number>-<description>`

- 타입은 커밋 메시지 타입과 일치 (`feat`, `fix`, `refactor`, `docs`, `chore` 등)
- description은 영어 소문자 + 하이픈 (kebab-case)
- 예시: `feat/12-add-boiler`, `fix/34-checksum-error`, `docs/45-update-readme`

### 브랜치 생성 전 원격 동기화

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b <branch-name>
```

## 7. Pull Request 작성 규칙

- `.github/PULL_REQUEST_TEMPLATE.md` 양식 준수
- PR 제목 형식: 커밋 메시지 제목과 동일 (`<emoji> <type>(<scope>): <subject>`)
- PR 본문 하단에 `Closes #<이슈 번호>` 작성

## 8. 추적 제외 파일 언급 금지

`.gitignore` 대상 파일(`.cursor/`, `.cursorrules/`, `.vscode/`, `.env` 등)은 커밋 메시지·PR 어디에도 언급하지 않습니다.

## 9. 이슈 기반 작업 시작

이슈 번호를 선언받으면 바로 구현 계획을 작성하지 않습니다. 먼저 구현 범위·설계 의도·접근 방식에 대해 질문하여 합의한 후 계획을 수립합니다.

## 10. 이슈 템플릿 선택 기준

| 템플릿 | 선택 기준 |
|--------|-----------|
| `feature` | 새로운 기능 추가 |
| `bug` | 버그 수정, 예상치 못한 동작 수정 |
| `refactor` | 외부 동작 변화 없는 코드 구조·설계 개선 |
| `chore` | 유지보수, 설정 변경, 의존성 업데이트, 문서 작업 |
