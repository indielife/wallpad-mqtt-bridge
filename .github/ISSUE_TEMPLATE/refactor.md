---
name: Refactor
about: Improve code structure or design without changing external behavior
title: "[refactor] "
labels: ["type:refactor"]
---

<!-- [GUIDELINE] 이슈 생성 시 assignee를 지정하지 말 것. -->

> [!IMPORTANT]
> **작업 시작 전 필수 가이드라인**:
> 1. **계획 수립 전 협의**: 상세 구현 계획(Implementation Plan)을 작성하기 전에, 먼저 사용자(USER)와 구현 방향 및 세부 접근 방식에 대해 대화를 나누고 얼라인을 맞추세요.
> 2. **개발 표준 준수**: 프로젝트 루트의 `.cursorrules` 폴더를 반드시 열어보고 코딩 표준 및 주의사항을 준수하여 작업을 진행하세요.

## Background

<!-- 이 리팩토링이 왜 필요한가? 현재 구조의 어떤 문제를 해결하는가? -->

## Branch Name

<!-- [GUIDELINE] 이슈 카드 생성 시 <issue-number> 플레이스홀더를 수정하지 않고 그대로 본문을 업로드할 것. 생성 이후 번호를 채우기 위해 본문을 재수정(API 재호출)하여 토큰을 낭비하지 말 것. -->
- `refactor/<issue-number>-<description>` (e.g., `refactor/123-split-transport-layer`)

## Approach

<!-- 리팩토링 방식의 간략한 개요를 작성. 외부 동작이 변경되지 않음을 어떻게 보장할지 포함할 것. -->

## Scope

- In:
- Out:

## Affected files

<!-- 예상되는 수정/추가/삭제 파일 목록을 작성. 잘 모르는 경우 "TBD - <영역> 참조"로 작성. -->

-

## Tasks

- [ ]

## Done when

<!-- [GUIDELINE] ruff 항목과 회귀 테스트 항목은 항상 포함. 나머지는 작업 성격에 맞는 항목만 선택해 활성화할 것. -->
- [ ] 외부 동작 변경 없음 (기존 테스트 수정 없이 통과)
- [ ] `ruff check` / `ruff format` clean
<!-- - [ ] 단위 테스트 추가 (새로운 구조에 대한 커버리지 보완) -->
<!-- - [ ] 문서 업데이트 (구조 변경이 아키텍처 문서에 영향을 줄 경우) -->

## Sequence position

<!-- 선택 사항. 이 이슈가 다른 이슈에 의존하거나 다른 이슈를 차단할 때만 사용. -->

- Depends on:
- Blocks:
- Refs:
