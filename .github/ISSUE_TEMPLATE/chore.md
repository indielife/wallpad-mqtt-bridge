---
name: Chore
about: Maintenance, configuration, dependency updates, or other miscellaneous work
title: "[chore] "
labels: ["type:chore"]
---

<!-- [GUIDELINE] 이슈 생성 시 assignee를 지정하지 말 것. -->

## Background

<!-- 이 작업이 왜 필요한가? -->

## Branch Name

<!-- [GUIDELINE] 이슈 카드 생성 시 <issue-number> 플레이스홀더를 수정하지 않고 그대로 본문을 업로드할 것. 생성 이후 번호를 채우기 위해 본문을 재수정(API 재호출)하여 토큰을 낭비하지 말 것. -->
- `<type>/<issue-number>-<description>` (e.g., `chore/123-update-dependencies`, `refactor/123-split-modules`)

## Approach

<!-- 접근 방식의 간략한 개요를 작성. 일반적인 작업의 경우 생략하거나 짧게 작성하되, 명확하지 않은 결정 사항이 있다면 상세히 기술. -->

## Scope

- In:
- Out:

## Affected files

<!-- 예상되는 수정/추가/삭제 파일 목록을 작성. 아직 잘 모르는 경우 "TBD - <영역> 참조"로 작성. -->

-

## Tasks

- [ ]

## Done when

<!-- [GUIDELINE] ruff 항목은 항상 포함. 나머지는 작업 성격에 맞는 항목만 선택해 활성화할 것. -->
- [ ] `ruff check` / `ruff format` clean
<!-- - [ ] 기존 기능 회귀 없음 확인 -->
<!-- - [ ] 환경/의존성 변경사항 문서화 -->

## Sequence position

<!-- 선택 사항. 이 이슈가 다른 이슈에 의존하거나 다른 이슈를 차단할 때만 사용. -->

- Depends on:
- Blocks:
- Refs:
