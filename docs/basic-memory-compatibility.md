# Basic Memory 1.0.0 호환성 검증

확인일: 2026-10-31. **기존 시험 스크립트의 1.0 비호환을 수정하고, 임시 Vault에서 한글 검색 → 저장 → 수정 → 재조회까지 확인했다.** 실제 사용자 설정·Vault를 대상으로 실행한 설치 시험은 아니다.

## 환경과 결과

macOS, Python 3.12, 설치된 Basic Memory 1.0.0을 사용했다. 사용자 패키지는 업데이트하지 않았다. 임시 HOME·설정·캐시·DB·데모 Vault를 사용하고 자동 업데이트를 껐다. 임베딩 모델 다운로드가 불가능한 조건(`HF_HUB_OFFLINE=1`)으로 실행했다.

| 검증 | 결과 |
|---|---|
| CLI 데모 | 14개 통과, 기본 검색 1개 경고, 실패 0개 |
| MCP stdio | 10개 통과, 기본 검색 1개 경고, 실패 0개 |
| 설정 병합·사전 검사 | 임시 Codex TOML·Claude JSON에서 미리보기 무수정, 적용·재조회, 기존 항목 보존, 재적용 무변경, `vault_doctor` 통과 |
| 단위 테스트 | 56개 통과. 버전별 인자 변환·구버전 호출 보존·환경 격리 회귀 테스트 포함 |

검색 시험은 한글 질의·접두어, 현재 요약/이력 필터, 결과 수 제한을 포함했다. 쓰기 시험은 생성·append·실패한 수정 후 본문 보존을 확인했다. CLI에서는 Markdown 대조와 백업 사본의 삭제·복구 후 재색인도 확인했다.

**경고의 의미:** 텍스트 색인은 완성됐지만 임베딩 생성은 실패했다. 1.0의 기본 hybrid 검색도 오류 응답을 반환했다. 이를 빈 검색 결과나 의미 검색 성공으로 처리하지 않았으며, 명시적 텍스트 검색으로 저장·검색 흐름을 검증했다.

## 확인하고 수정한 차이

| 항목 | 0.x 호출 | 1.0 호출·동작 |
|---|---|---|
| MCP 도구 | `search_notes`, `read_note`, `write_note`, `edit_note` | `bm_search`, `bm_read`, `bm_write`, `bm_edit` |
| 검색 인자 | `search_type`, `metadata_filters` | `mode`, `filters` |
| 편집 인자 | `operation` | `command` |
| CLI | `tool search-notes/read-note/write-note/edit-note` | `tool search/read/write/edit`, 스크립트에서는 `--json` 명시 |
| CLI 쓰기 폴더·검색 필터 | `--folder`, `--meta k=v` | `--directory`, `--filters '{"k":"v"}'` |
| 프로젝트 등록 | 등록 후 별도 색인 | 기본 등록이 색인을 기다림. 시험에서는 `--no-wait` 등록 후 별도로 색인해 등록과 임베딩 실패를 구분 |
| 없는 노트에 append | 새 노트 생성 관찰 | 오류 응답과 파일 미생성 확인 |
| 없는 문자열 치환 | 오류 플래그 없이 실패 본문이 오기도 함 | MCP 오류 플래그 반환, 기존 내용 보존 확인 |

기존 `search-notes` 명령의 거절과 MCP의 새 도구 목록을 실제로 확인했다. 스크립트는 CLI 버전과 MCP 도구 목록에 따라 호출을 선택한다. 공용 지침·검색 예시도 버전별 인자를 구분했다. 근거: [공식 1.0 변경 안내](https://github.com/basicmachines-co/basic-memory/blob/main/docs/1.0.md)와 설치된 1.0.0의 도움말·실제 호출 결과. 공식 main 문서는 이후 바뀔 수 있다.

## 재현

Basic Memory가 설치된 Python 3.12 환경에서 저장소 루트를 기준으로 실행한다.

```sh
python -B -m unittest discover -s tests -q
python -B scripts/demo_roundtrip.py --offline
python -B scripts/mcp_stdio_check.py --offline
```

실제 설정을 대상으로 하지 않는다. 각 스크립트는 임시 프로젝트·Vault·DB를 만들고 종료 시 삭제한다. `demo_roundtrip.py --keep`은 임시 파일을 의도적으로 남기므로 정리가 필요한 시험에서는 사용하지 않는다.

## 보존과 남은 범위

시험 전후 실제 클라이언트·Basic Memory 설정 및 개인 Vault Markdown 등 327개 보호 경로의 해시가 동일했고, 개인 Vault에 새 Markdown이 없었다. 이번 시험에서 임시로 만든 설정·프로젝트·Vault·DB·보조 파일은 정리하고 결과 요약만 저장소에 남겼다.

이번 결과는 도구·스크립트 계층의 검증이다. 1.0의 온라인 의미 검색, Windows·Linux, 터널·웹 연결, 실제 사용자 프로필 설치는 재검증하지 않았다. 0.x 호출 경로는 회귀 테스트로 보존했지만 이번에는 0.x 서버를 다시 실행하지 않았다. 실제 AI의 지침 자동 적용은 [별도 클라이언트 시험](setup-skill-verification.md)의 버전·범위를 참고한다.
