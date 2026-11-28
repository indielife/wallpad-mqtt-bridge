# Git 커밋 메시지 규칙 (Gitmoji + Conventional Commits)

## 릴리즈

릴리즈는 [릴리즈 절차](docs/release.md)를 따릅니다.
릴리즈 노트를 먼저 작성·검토하고 최종 검증 후 태그를 발행한 뒤,
GitHub 릴리즈와 HA 애드온 저장소의 버전·변경 내역을 갱신합니다.

## 커밋 메시지 구조

```text
<emoji> <type>(<scope>): <subject>

<body>

<footer>
```

## 제목(Subject) 규칙

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

## 본문(Body) 규칙

- 한 줄 72자 이하
- `what` / `why` 중심, 구현 방법(`how`)은 지양
- 글머리 기호(`- `) 사용, 명사형 종결 — 어색할 경우 음슴체(`~함`, `~음`) 허용

## 바닥글(Footer) 규칙

- 이슈 종료: `Closes #<번호>` / 이슈 참조: `Ref #<번호>`
- 동일 이슈에 `Closes`와 `Ref` 중복 금지
- 여러 이슈: `Closes #17, #18` 또는 별도 라인

## 커밋 전 검사

```bash
.venv/bin/pre-commit run --all-files
```

pre-commit 훅은 ruff(check·format)·파일 위생 검사와 함께 `pytest`를 실행합니다.
커밋이 성립하려면 테스트가 모두 통과해야 하며, 이는 한 PR 안에서 테스트가 깨진 채로
커밋이 누적되는 것을 로컬에서 미리 차단합니다. (CI는 push된 브랜치 최종 상태를 별도로 검증합니다.)

## 줄바꿈 정책

작성물의 종류(surface)마다 렌더링·diff 특성이 달라 줄바꿈 기준을 다르게 적용합니다.

| Surface | 줄바꿈 | 근거 / 강제 수단 |
|---------|--------|------------------|
| 코드 | hard wrap | `ruff.toml`의 `line-length`가 SoT(현재 100). ruff가 강제 |
| 커밋 메시지 | hard wrap | [제목](#제목subject-규칙) 50자·[본문](#본문body-규칙) 72자 |
| 마크다운 문서 | 100칼럼 이내, 문장·절 경계 hard wrap | 실제 개행으로 git diff가 문장·절 단위로 떨어지게 함 (아래 세부 규칙) |
| Issue / PR 본문 | no wrap | GitHub 코멘트는 문단 내 단일 개행을 `<br>`로 렌더 |

### 마크다운 hard wrap 세부 규칙

- **한 문장을 기본 한 줄로 둡니다.**
  문장이 100칼럼을 넘으면 주요 절 경계(쉼표·연결어미)에서 한 번만 끊고,
  짧은 문장을 억지로 더 쪼개지 않습니다.
- 소스(raw)에는 실제 개행이 들어가지만, GFM은 문단 내 단일 개행을 공백으로 렌더하므로
  GitHub에서는 줄바꿈 없이 흐르는 텍스트로 보입니다.
  따라서 `<br>`, 줄 끝 공백 2개, 줄 끝 백슬래시는 사용하지 않습니다.
- **반드시 어절(공백) 경계에서만 접습니다.**
  한글 단어 중간에서 접으면 렌더 시 공백이 끼어 단어가 깨집니다.
- 리스트·표·코드블록처럼 개행이 구조적 의미를 갖는 곳은 reflow하지 않습니다.

## 문서 계층과 클래스명

클래스 rename이 문서 정합성을 깨지 않도록, 구체성이 사는 위치를 계층으로 고정합니다.

| 문서 | 성격 | 타입 이름 |
|------|------|-----------|
| `docs/adr/` | append-only 기록 | 역할·포트(계약)만. 구현 클래스명 금지 (세부: [adr/README.md](docs/adr/README.md)) |
| `docs/architecture.md` | 살아있는 문서 (상위) | 아키텍처 골격 타입(`BaseTransport`·`Panel`·`CategoryController`·`StateSynchronizer`)은 허용. 개수가 불어나는 어댑터는 역할 중심으로 서술 |
| `docs/sequences.md` · 코드 | 살아있는 문서 (하위) | **구현 클래스명·상호작용 시퀀스가 사는 곳.** rename 시 여기와 코드만 갱신 |

- **계약 표면 타입**(예: `BaseTransport` 인터페이스, HA MQTT Discovery·토픽 계약,
  `CategoryController`의 `apply_ha_command`/`apply_rs485_state` 표면)은 경계 계약 그 자체라
  상위 문서에 명시합니다. rename은 계약 변경이므로 문서 전체 갱신을 동반합니다.
- **아키텍처 골격 타입**(`Panel`·`StateSynchronizer` 등 시스템의 뼈대를 이루는 구조)도
  상위 문서가 명시합니다 — 이들을 빼면 아키텍처 서술 자체가 성립하지 않기 때문입니다.
- **개수가 불어나는 구현 어댑터**(transport 구현 `SerialTransport`·`SocketTransport`,
  데코레이터 `ReconnectingTransport`·`BusArbitrationTransport`, 기기별 leaf 빌더 등)는
  churn이 잦으므로 상위 문서에서는 역할("시리얼/소켓 transport", "재연결·버스중재 데코레이터",
  "기기 빌더")로 부르고, 구체 클래스명의 전체 인벤토리와 시퀀스는 하위 문서·코드가 소유합니다.

## 브랜치 명명 규칙

- 이슈가 있는 작업: `<type>/<issue-number>-<description>`
- 이슈 없이 진행하는 작업: `<type>/<description>`

- 타입은 커밋 메시지 타입과 일치 (`feat`, `fix`, `refactor`, `docs`, `chore` 등)
- description은 영어 소문자 + 하이픈 (kebab-case)
- 예시: `feat/12-add-boiler`, `fix/34-checksum-error`, `docs/45-update-readme`

### 브랜치 생성 전 원격 동기화

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b <branch-name>
```

## Pull Request 작성 규칙

- [.github/pull_request_template.md](.github/pull_request_template.md) 양식 준수
- PR 제목 형식: 커밋 메시지 제목과 동일 (`<emoji> <type>(<scope>): <subject>`)
- `Related issues`에 종료할 이슈는 `Closes #N`, 일부 기여는 `Ref #N`으로 연결합니다.
- 연결할 이슈가 없으면 해당 절을 생략합니다. 같은 이슈에 `Closes`와 `Ref`를 중복하지 않습니다.

## 추적 제외 파일 언급 금지

`.gitignore` 대상 파일(`.env` 등)은
커밋 메시지·PR 어디에도 언급하지 않습니다.

## 이슈 템플릿 선택 기준

| 템플릿 | 선택 기준 |
|--------|-----------|
| `feature` | 새로운 기능 추가 |
| `bug` | 버그 수정, 예상치 못한 동작 수정 |
| `refactor` | 외부 동작 변화 없는 코드 구조·설계 개선 |
| `chore` | 유지보수, 설정 변경, 의존성 업데이트, 문서 작업 |
| `spike` | 구현 전 조사·실험으로 판단 근거를 확보하는 작업 |

### 이슈·PR 템플릿 작성

- 이슈·PR 본문의 섹션 제목과 구조 키워드는 영어로 유지합니다.
  설명과 안내 주석은 한국어로 작성합니다.
  `In`, `Out`, `Depends on`, `Blocks`, `Refs`, `Closes`, `Ref`를 유지합니다.
- 이슈의 `Background`, `Scope`, `Done when`에 문제·범위·관찰 가능한 완료 조건을 적습니다.
  `Approach`와 `Tasks`는 필요할 때만 작성하고 상세 구현 계획은 착수 시 수립합니다.
- `Starting points`에는 알고 있는 관련 경로와 이유를 적습니다.
  탐색은 해당 경로부터 시작하고 필요한 의존 관계를 따라 확장합니다.
  수정 파일을 확정하거나 탐색 범위를 제한하는 목록이 아니며 경로를 추측하지 않습니다.
- 이슈 본문에는 브랜치명을 적지 않습니다. 실제 브랜치는 PR에서 확인합니다.
- `Dependencies`는 관계가 있을 때만 작성하고 빈 항목은 삭제합니다.
  `Depends on`과 `Blocks`에는 착수·병합·운영 활성화 중 어느 단계의 조건인지 명시합니다.
- 일반 CI 검사 통과 여부와 테스트 개수를 고정 체크박스로 반복하지 않습니다.
  필수 검사 수행 의무는 유지하며 검사 도입·범위 변경이 목표이면 완료 조건에 포함합니다.
- PR의 `Test Plan`에는 핵심 검증 시나리오·실행 조건·관찰 결과와 근거를 적습니다.
  자동 테스트와 실제 연동·운영 확인을 구분합니다.
  미검증 범위와 완료 판단에 미치는 영향은 `Limitations and follow-up`에 적습니다.
- 이슈의 `Outcome`은 PR 머지 준비 시 목표 달성 여부·최종 결정·관련 PR을 기록합니다.
  남은 작업과 이슈 종료 가능 여부를 적고 병합·운영 확인으로 달라지면 갱신합니다.
  PR 없이 끝나는 작업은 종료 판단 시 결과와 근거를 기록합니다.
  작은 작업은 결과 한 문장과 근거 링크로 충분하며 검증 상세는 PR·조사 기록에 연결합니다.
- `spike`는 조사 질문·방법·종료 기준과 확인한 사실·추정·미검증 범위를 구분합니다.
  채택·보류·기각도 유효한 결론이며 채택안 구현 성공을 조사 완료 조건으로 두지 않습니다.
  조사 범위를 벗어나는 구현은 범위를 합의하거나 후속 이슈로 분리합니다.

`spike`는 기존 `chore:` 제목과 `type:chore` 라벨을 사용합니다.
