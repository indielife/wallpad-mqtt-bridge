# 릴리즈 절차

이 문서는 소스 릴리즈와 Home Assistant(HA) 애드온 배포를 순서대로 진행하는 수동 절차입니다.
다음 릴리즈부터는 **릴리즈 노트를 먼저 작성·검토하고, 최종 검증 후 태그를 발행**합니다.

## 버전과 저장소의 역할

- 소스 저장소 `indielife/wallpad-mqtt-bridge`의 `v<버전>` 태그가 배포할 소스 커밋을 고정합니다.
- 소스의 `pyproject.toml`과 애드온의 `config.yaml`은 `v` 없는 버전을 사용합니다.
- GitHub 릴리즈는 해당 태그의 변경 내용·지원 범위·검증 근거를 공개합니다.
- `indielife/ha-addons`는 HA 설치용 설정·Dockerfile·사용 안내를 제공합니다.
  HA는 설치·업데이트 시 `BUILD_VERSION`에 대응하는 소스 태그로 Docker 이미지를 빌드합니다.
- GitHub 릴리즈에는 별도 wheel·바이너리·Docker 이미지를 첨부하지 않습니다.
  `scripts/`의 빌드·복사 도구는 개발 편의용이며 사용자 배포 경로는 애드온 저장소입니다.

이미 배포한 태그는 다른 커밋으로 옮기거나 재생성하지 않습니다.
소스 변경은 새 버전으로 배포합니다.

## 1. 범위 결정과 릴리즈 노트 작성

1. 이전 태그 이후 포함할 변경과 PR을 확인하고 릴리즈 버전을 정합니다.
2. 소스 패키지 버전과 필요한 설정·문서 변경을 PR로 준비합니다.
   소스에서 버전을 읽는 위치와 애드온 설정의 정합성도 확인합니다.
3. `docs/releases/v<버전>.md`에 노트 초안을 작성하고, 코드 변경과 함께 검토합니다.
   기존 노트는 [v0.1.0 릴리즈 노트](releases/v0.1.0.md)를 참고합니다.
4. 아래 항목과 확인되지 않은 검증 항목을 기록합니다.

릴리즈 노트에는 다음 내용을 포함합니다.

- 기준 태그, 대상 소스의 전체 커밋 SHA, 이전 버전과 비교 범위, 주요 포함 PR
- 사용자에게 영향을 주는 기능·수정·설정 변경과 마이그레이션 안내
- 제조사·기기·연결 방식별 지원 범위와 알려진 제약
- HA 애드온 저장소 등록·설치·업데이트 경로
- 검증한 애드온 커밋에 고정한 버전별 설정·설치 안내 링크
- 해당 소스 커밋의 CI 실행 링크와 검사별 결과
- 실제 검증한 소스 및 `ha-addons` 커밋, 빌드 버전 인수 또는 이미지 식별자
- 빌드 아키텍처와 HA 검증 환경(HA 버전·장비 아키텍처·연결 방식)
- 빌드·설치·기동·MQTT 연결·기기 등록·제어 등 실제 확인한 항목과 결과

검증하지 않은 환경이나 기능은 미확인으로 표시합니다.
빌드 성공을 HA에서의 기동·실기기 제어 성공으로 대신하지 않습니다.
다른 커밋에서 얻은 테스트 수나 운영 결과를 해당 릴리즈의 검증 결과로 기록하지 않습니다.

## 2. 최종 검증과 대상 커밋 확정

1. 노트 초안을 포함한 소스 PR의 검사·리뷰를 완료하고 `main`에 반영합니다.
2. 원격을 동기화하고 실제 태그를 붙일 소스 커밋을 확정합니다.
3. 그 커밋에서 버전과 변경 범위를 확인하고 CI 성공을 확인합니다.
   로컬 검사는 프로젝트 가상환경을 활성화하여 실행합니다.

   ```bash
   source .venv/bin/activate
   ruff check .
   ruff format --check .
   pytest
   pre-commit run --all-files
   ```

4. `ha-addons`에서 후보 버전의 설정·Dockerfile을 준비하고 검증 계획을 확인합니다.
   태그가 필요한 실제 애드온 빌드는 태그 발행 후 확인하며, 실패하면 HA 배포를 중단합니다.
5. 노트의 대상 SHA와 CI 링크를 확정합니다.
   노트를 담은 커밋의 SHA를 그 파일 안에 미리 넣을 수 없으므로, 사본에서 최종 본문을 확정합니다.

```bash
git fetch origin
git checkout main
git pull --ff-only origin main

# 예시 버전입니다. 합의한 버전으로 바꾸고, 검토한 커밋과 일치하는지 확인합니다.
release_version=0.1.1
release_tag="v${release_version}"
release_sha=$(git rev-parse HEAD)
release_notes="/tmp/wallpad-release-${release_tag}.md"
cp "docs/releases/${release_tag}.md" "$release_notes"
git show --no-patch "$release_sha"
```

`release_notes` 사본에 전체 SHA·CI 링크·최종 검증 결과를 채우고 다시 검토합니다.
태그에 포함된 초안은 GitHub 릴리즈에 최종 근거가 있음을 안내할 수 있습니다.
발행 후 저장소의 노트도 최종 본문과 맞추되, 기존 태그는 유지합니다.

## 3. 태그 생성·푸시

노트 검토와 소스 검증을 마친 뒤에만 확정한 커밋에 태그를 붙입니다.
원격에 동일한 태그가 이미 있다면 아래 생성 명령을 실행하지 말고 기존 태그 절차를 따릅니다.

```bash
git tag -a "$release_tag" "$release_sha" -m "Wallpad MQTT Bridge ${release_tag}"
git push origin "$release_tag"
git ls-remote origin "refs/tags/${release_tag}" "refs/tags/${release_tag}^{}"
git rev-parse "${release_tag}^{commit}"
```

annotated 태그는 원격 출력의 `^{}` 항목이 소스 커밋 SHA입니다.
lightweight 태그는 태그 참조 자체가 소스 커밋을 가리킵니다.
원격·로컬 태그와 노트의 SHA가 일치해야 합니다.

## 4. GitHub 릴리즈 발행

GitHub의 새 릴리즈 화면에서 **기존 태그를 선택**하고 검토한 노트를 게시합니다.
CLI를 사용할 때는 원격 태그가 없으면 실패하도록 `--verify-tag`를 지정합니다.

```bash
gh release create "$release_tag" \
  --repo indielife/wallpad-mqtt-bridge \
  --verify-tag --title "Wallpad MQTT Bridge ${release_tag}" \
  --notes-file "$release_notes"
gh release view "$release_tag" --repo indielife/wallpad-mqtt-bridge
```

공개 페이지의 태그·소스 커밋·본문·링크와 최신 릴리즈 표시를 확인합니다.
본문의 오기나 검증 근거 보완은 노트 수정으로 처리합니다.
소스를 바꿔야 하면 새 버전을 준비합니다.

이미 발행한 노트를 수정할 때는 문서 PR을 검토·병합한 뒤,
기존 GitHub 릴리즈 본문도 병합한 파일로 갱신합니다.
태그와 소스 커밋은 유지하고, 공개 본문과 저장소 파일의 일치를 확인합니다.

```bash
gh release edit "$release_tag" --repo indielife/wallpad-mqtt-bridge \
  --notes-file "docs/releases/${release_tag}.md"
gh release view "$release_tag" --repo indielife/wallpad-mqtt-bridge \
  --json body --jq '.body | rtrimstr("\n")' > "/tmp/wallpad-release-${release_tag}-published.md"
diff -u "docs/releases/${release_tag}.md" "/tmp/wallpad-release-${release_tag}-published.md"
```

## 5. HA 애드온 저장소 갱신

GitHub 릴리즈 발행 후 `indielife/ha-addons`의 최신 `main`에서 변경을 준비합니다.

1. `wallpad-mqtt-bridge/config.yaml`의 `version`을 릴리즈 버전으로 맞춥니다.
2. `wallpad-mqtt-bridge/Dockerfile`의 `ARG BUILD_VERSION` 기본값을 같은 버전으로 맞춥니다.
   `git clone --branch "v${BUILD_VERSION}"`이 해당 태그를 가져오는지 확인합니다.
3. `wallpad-mqtt-bridge/README.md`의 버전·지원 범위·태그 기준 문서 링크를 갱신합니다.
4. `wallpad-mqtt-bridge/CHANGELOG.md`에 버전별 변경 요약과 GitHub 릴리즈 링크를 추가합니다.
   이 파일은 HA에서 업데이트 내용을 확인하는 경로입니다.
5. 애드온 저장소 루트에서 버전 지정 빌드와 기본 빌드를 검증합니다.

   ```bash
   docker build --build-arg "BUILD_VERSION=${release_version}" \
     -t "wallpad-mqtt-bridge-addon:${release_version}" ./wallpad-mqtt-bridge
   docker build -t wallpad-mqtt-bridge-addon:default ./wallpad-mqtt-bridge
   ```

6. 사용한 애드온 커밋·소스 SHA·이미지 식별자·아키텍처와 검사 결과를 기록합니다.
7. PR을 검토하고 필요한 변경을 애드온 저장소 `main`에 반영합니다.
   빌드 실패나 버전·소스 불일치가 있으면 배포를 진행하지 않습니다.

태그와 같은 버전을 이미 배포한 경우에는 기존 검증 근거와 현재 설정을 대조합니다.
문서만 보완했다면 불필요하게 버전을 올리지 않고, 코드 변경이 없는 사실을 기록합니다.

## 6. HA 확인과 검증 기록 보완

1. HA에서 애드온 저장소를 새로고침합니다.
2. 표시 버전과 변경 내역·릴리즈 링크를 확인합니다.
3. 애드온 변경이 있으면 업데이트하고 기동·MQTT 연결·기기 등록·정상 동작을 확인합니다.
4. HA 버전·장비 아키텍처·연결 방식, 실제 배포 식별자와 결과를 기록합니다.
5. 릴리즈 노트와 관련 이슈에 검증 결과 및 미확인 항목을 반영합니다.

기록을 확보하지 못한 HA 확인 항목은 완료로 표시하지 않습니다.
기존 버전의 설치 성공 기록과 이번 저장소 새로고침·변경 내역 표시 확인은 구분합니다.

## 기존 v0.1.0 태그에 노트를 발행하는 경우

`v0.1.0`은 릴리즈 노트를 준비하기 전에 생성한 예외입니다.
태그는 `592d53b40e82085b4fb50c04ea3cef730069685b`를 가리키며 그대로 사용합니다.
태그 이후 `main`에 반영된 변경은 이 버전에 포함하지 않습니다.

```bash
git fetch origin --tags
git rev-parse 'v0.1.0^{commit}'
gh release create v0.1.0 --repo indielife/wallpad-mqtt-bridge \
  --verify-tag --title 'Wallpad MQTT Bridge v0.1.0' \
  --notes-file docs/releases/v0.1.0.md
```

태그 생성 후에도 릴리즈 본문을 작성·발행할 수 있습니다.
이미 릴리즈가 있다면 새로 만들지 않고 기존 본문과 근거를 확인·보완합니다.
이번 버전은 [#81의 검증 기록][issue81]을 근거로 사용하며,
실제 HA 환경 세부 정보와 검증 범위 중 미확인 항목은 노트에 명시합니다.

[issue81]: https://github.com/indielife/wallpad-mqtt-bridge/issues/81
