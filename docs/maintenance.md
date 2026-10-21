# 백업·복구·업데이트·제거

이 저장소의 도구는 Vault 노트를 삭제하거나 이동하지 않음. 아래는 사용자가 직접 수행하는 절차이며, 실제 Vault에 적용하기 전 항상 백업을 먼저 만듦
점검 범위(2026-10-22, 임시 데모 Vault·임시 설정 폴더): 설정 병합 백업의 생성과 복구(바이트 동일), Vault 폴더 복사본에서 노트 삭제 → 복구 → `reindex` 후 재검색, `project remove`의 파일 보존과 기본 프로젝트 제한. 실제 개인 Vault에는 적용하지 않았고, 업데이트·`launchctl bootout` 등 나머지 절차는 문서만 있음(미실행)

## 무엇을 백업하나

| 대상 | 중요도 | 비고 |
|---|---|---|
| Vault 폴더 (Markdown 원본) | **필수** | 노트의 정본. 폴더 복사만으로 충분 |
| MCP 설정 파일 (Codex·Claude) | 권장 | `merge_mcp_config.py --apply`가 `.bak-타임스탬프`를 자동 생성 |
| Basic Memory 설정·DB (아래 설정 폴더) | 선택 | 검색 DB는 `reindex`로 Markdown에서 다시 만들 수 있음(임시 환경에서 확인). 프로젝트 등록 정보는 `config.json` |
| 터널 키·프로필 | 별도 보관 | 키는 저장소·Vault에 넣지 않음. 이 저장소가 다루지 않음 |

Basic Memory 설정 폴더는 `BASIC_MEMORY_CONFIG_DIR`이 있으면 그 폴더, 없고 `XDG_CONFIG_HOME`이 있으면 `$XDG_CONFIG_HOME/basic-memory`, 둘 다 없으면 `~/.basic-memory`임 (0.22.1 코드와 임시 환경 시험으로 확인). `vault_doctor.py`도 같은 순서로 찾음

Vault 백업 예 (시각이 붙은 폴더로 복사. 경로는 예시)

```sh
cp -R /ABSOLUTE/PATH/AI-Vault "/ABSOLUTE/PATH/backups/AI-Vault-$(date +%Y%m%d-%H%M%S)"
```

백업 폴더는 Vault 밖에 두고 공개 저장소에 올리지 않음 (`.gitignore`에 `backups/` 포함)

## 복구

1. 설정 병합을 되돌리려면: 백업 파일 `config.toml.bak-…`을 원래 이름으로 복사함
2. Vault 노트를 되돌리려면: 백업 폴더의 해당 파일만 복사함 (폴더 통째 덮어쓰기 전에 현재 상태를 한 번 더 백업)
3. 복구 후 `basic-memory reindex --project <ID> --full`로 색인을 다시 만들고 `vault_doctor.py`로 확인함

## 업데이트

1. 업데이트 전에 위 백업을 만들고 현재 버전을 기록함: `basic-memory --version`
2. Basic Memory를 설치 때 쓴 방식으로 업데이트함 (`basic-memory update`는 설치 방식이 지원할 때만 동작하며 이 저장소는 실행하지 않았음)
3. 업데이트 후 `vault_doctor.py`와 [연결 시험](../prompts/roundtrip-test.md)을 다시 실행함. 이전 버전의 검증 결과를 새 버전에 그대로 적용하지 않음
   `scripts/demo_roundtrip.py`와 `scripts/mcp_stdio_check.py`도 다시 돌리면 문서화한 동작이 새 버전에서도 유지되는지 격리 환경에서 확인할 수 있음. 실제로 0.23.2는 임베딩 모델을 받지 못할 때 `reindex`의 종료 코드가 0.22.1과 달랐음 ([기능 상태](status.md))
4. 저장소의 문서·스크립트를 갱신할 때는 `git pull`로 가져오고, 로컬에서 바꾼 설정 사본은 저장소 밖에 두면 충돌하지 않음

## 제거 (연결만 끊기)

노트는 그대로 두고 연결만 제거하는 순서

1. AI 클라이언트의 MCP 설정에서 `basic-memory` 항목을 지움 (백업을 먼저 만들고 해당 항목만 삭제)
2. 터널을 쓰고 있었다면 터널 프로세스·자동 실행 등록을 해제함 (macOS LaunchAgent는 `launchctl bootout`과 plist 삭제가 일반적인 방법이나 이 저장소에서 실행해 검증하지 않았음)
3. 필요하면 Basic Memory에서 프로젝트 등록만 해제함: `basic-memory project remove <ID> --local`. `--delete-notes`를 **붙이지 않으면** 노트 파일은 남음 (임시 데모에서 확인). 기본 프로젝트는 지울 수 없으므로 먼저 `basic-memory project default <다른ID>`로 바꿔야 함. `--delete-notes`는 파일을 지우는 옵션이라 사용하지 않음
4. Vault 폴더는 사용자 데이터이므로 이 단계에서 지우지 않음

## 데이터 이전 (참고)

기존 긴 노트를 현재 요약·상세 이력으로 나누는 작업은 실제 노트를 바꾸는 일이라 이 저장소의 도구는 자동화하지 않음. 절차와 롤백 기준은 [노트 구조 문서](context-structure.md#기존-긴-노트를-전환할-때)를 따름
