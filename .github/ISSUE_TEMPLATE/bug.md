---
name: Bug
about: Report a defect or unexpected behavior
title: "[fix] "
labels: ["type:fix"]
---

> [!IMPORTANT]
> **작업 시작 전 필수 가이드라인**:
> 1. **계획 수립 전 협의**: 상세 구현 계획(Implementation Plan)을 작성하기 전에, 먼저 사용자(USER)와 구현 방향 및 세부 접근 방식에 대해 대화를 나누고 얼라인을 맞추세요.
> 2. **개발 표준 준수**: 프로젝트 루트의 `.cursorrules` 파일을 반드시 열어보고 코딩 표준 및 주의사항을 준수하여 작업을 진행하세요.

## Background

<!-- One or two sentences: what is broken and why does it matter? -->

## Branch Name

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

<!-- Paste relevant logs, stack traces, or screenshots. -->

## Approach

<!-- Brief outline of the fix approach once root cause is identified.
May start empty and be filled in as triage progresses. -->

## Scope

- In:
- Out:

## Affected files

<!-- Files expected to change for the fix. Write "TBD - see <area>"
if root cause is not yet localized. -->

-

## Tasks

- [ ]

## Done when

- [ ] Reproduction no longer fails
- [ ] Regression test added (`pytest`)
- [ ] `ruff check` / `ruff format` clean

## Sequence position

<!-- Optional. -->

- Depends on:
- Blocks:
- Refs:
