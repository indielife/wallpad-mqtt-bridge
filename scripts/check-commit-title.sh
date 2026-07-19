#!/usr/bin/env bash
# commit-msg 훅: 제목 줄에 이슈/PR 번호(#N)를 넣지 못하게 막는다.
# 이슈 참조는 본문 트레일러(Closes #N / Ref #N)로만 작성한다 (CONTRIBUTING.md 참조).
set -euo pipefail

msg_file="$1"
title="$(head -n1 "$msg_file")"

if [[ "$title" =~ \(#[0-9]+\)[[:space:]]*$ ]]; then
  echo "❌ 커밋 제목에 이슈/PR 번호를 넣지 마세요: $title"
  echo "   이슈 참조는 본문 트레일러(Closes #N / Ref #N)에 작성합니다."
  exit 1
fi
