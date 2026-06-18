---
name: Bug
about: Report a defect or unexpected behavior
title: "[fix] "
labels: ["type:fix"]
---

> [!IMPORTANT]
> **작업 시작 전 필수 가이드라인**:
> 1. **계획 수립 전 협의**: 상세 구현 계획(Implementation Plan)을 작성하기 전에, 먼저 사용자(USER)와 구현 방향 및 세부 접근 방식에 대해 대화를 나누고 얼라인을 맞추세요.
> 2. **개발 표준 준수**: 프로젝트 루트의 `.cursorrules` 폴더를 반드시 열어보고 코딩 표준 및 주의사항을 준수하여 작업을 진행하세요.

## Background

<!-- 한두 문장: 어떤 부분이 고장 났으며 왜 중요한가? -->

## Branch Name

<!-- [GUIDELINE] 이슈 카드 생성 시 <issue-number> 플레이스홀더를 수정하지 않고 그대로 본문을 업로드할 것. 생성 이후 번호를 채우기 위해 본문을 재수정(API 재호출)하여 토큰을 낭비하지 말 것. -->
- `<type>/<issue-number>-<description>` (e.g., `fix/123-checksum-error`)

## Steps to reproduce

1.
2.
3.

### Expected behavior

### Actual behavior

### Environment

- HA version:
- Supervisor version:
- Addon version:
- Commit:

### Logs / screenshots

<!-- 관련된 로그, 스택 트레이스 또는 스크린샷을 첨부. -->

## Approach

<!-- 근본 원인이 파악되면 해결 방식의 간략한 개요를 작성. 분석 진행 상황에 따라 처음에 비워두고 나중에 채워도 됨. -->

## Scope

- In:
- Out:

## Affected files

<!-- 수정될 것으로 예상되는 파일 목록. 근본 원인이 아직 파악되지 않은 경우 "TBD - <영역> 참조"로 작성. -->

-

## Tasks

- [ ]

## Done when

- [ ] Reproduction no longer fails
- [ ] Regression test added (`pytest`)
- [ ] `ruff check` / `ruff format` clean

## Sequence position

<!-- 선택 사항 -->

- Depends on:
- Blocks:
- Refs:
