---
name: Feature
about: Propose a new feature
title: "feat: "
labels: ["type:feat"]
---

<!-- [GUIDELINE] 이슈 생성 시 assignee를 지정하지 말 것. -->

## Background

<!-- 이 작업이 왜 필요한가? -->

## Branch Name

<!-- [GUIDELINE] 이슈 카드 생성 시 <issue-number> 플레이스홀더를 수정하지 않고 그대로 본문을 업로드할 것. 생성 이후 번호를 채우기 위해 본문을 재수정(API 재호출)하여 토큰을 낭비하지 말 것. -->
- `<type>/<issue-number>-<description>` (e.g., `feat/123-add-search-filter`)

## Approach

<!-- 구현 방식의 간략한 개요를 작성. -->

## Scope

- In:
- Out:

## Affected files

<!-- 예상되는 수정/추가/삭제 파일 목록을 작성. 잘 모르는 경우 구현자가 범위를 열어두고 넓은 범위의 코드 검색 전에 질문할 수 있도록 "TBD - <영역> 참조"로 작성. -->

-

## Tasks

- [ ]

## Done when

- [ ] end-to-end 동작 검증 완료
- [ ] 단위 테스트 추가 (`pytest`)
- [ ] 문서 업데이트
- [ ] `ruff check` / `ruff format` clean

## Sequence position

<!-- 선택 사항. 이 이슈가 다른 이슈에 의존하거나 다른 이슈를 차단할 때만 사용. -->

- Depends on:
- Blocks:
- Refs:
