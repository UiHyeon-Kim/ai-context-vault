# 빠른 시작: 설치부터 첫 기록까지

목표: “README 읽기 → 검색 → 기록 → 재조회”가 되는 상태 만들기 (소요 시간은 측정하지 않았음)
먼저 연습하려면 저장소의 [데모 Vault](../examples/demo-vault/README.md)를 복사해서 쓰면 됨 (가상 프로젝트, 개인 정보 없음)
검증한 환경: macOS + Basic Memory 0.22.1. Windows·Linux는 단위 테스트만 CI에서 통과했고 Basic Memory 연동은 미검증 ([지원 환경](status.md#지원-환경))
아래 셸 예시는 POSIX(macOS·Linux) 문법임. Windows에서는 경로 표기와 명령을 환경에 맞게 바꿔야 하며 검증하지 않았음

## 0. 준비물

- **Python 3.11 이상**: `python3 --version`으로 확인. macOS 기본 `/usr/bin/python3`는 3.9라서 이 저장소의 스크립트가 “Python 3.11 이상이 필요합니다” 메시지로 멈춤. 이때는 3.11 이상 인터프리터(예: Homebrew의 `python3.12`)로 실행
- [Basic Memory 설치](https://docs.basicmemory.com/start-here/quickstart-local) 완료, `basic-memory --version` 동작
- Markdown 폴더 하나 (Obsidian Vault여도 되고 새 폴더여도 됨). 기존 노트가 있으면 **먼저 폴더를 통째로 백업** ([백업·복구](maintenance.md))

## 1. 이름 정하기

기본값을 쓰면 됨: 프로젝트 ID `ai-vault`, 폴더 `AI-Vault`. 다른 이름을 쓰려면 먼저 [이름 구분](naming.md) 확인

## 2. 프로젝트 등록

```sh
basic-memory project add ai-vault /ABSOLUTE/PATH/AI-Vault --local
```

연습용이라면 데모 폴더를 **복사해서** 등록함 (원본 데모를 수정하지 않기 위해). `/tmp/demo-vault`는 예시 경로임

```sh
cp -R examples/demo-vault /tmp/demo-vault
basic-memory project add demo-vault /tmp/demo-vault --local
```

## 3. 사전 검사

```sh
python3 scripts/vault_doctor.py --vault /ABSOLUTE/PATH/AI-Vault --project ai-vault
```

확인하는 것: 실행 파일, Vault 폴더와 README, 프로젝트 ID와 폴더의 일치, 비밀값처럼 보이는 문자열(값은 출력하지 않음). 읽기 전용이며 아무것도 수정하지 않음
`[FAIL]`이 있으면 메시지대로 고친 뒤 다시 실행함. 4단계에서 설정 파일을 만든 뒤에는 `--config 파일경로`를 붙여 같은 검사를 한 번 더 실행함 (MCP 설정, 터널 프로필, LaunchAgent plist 지원)

## 4. AI 클라이언트에 연결

클라이언트마다 등록 방법이 다르며, 가능하면 **해당 앱이 제공하는 공식 명령**을 먼저 고려함 (앱이 설정 파일을 직접 관리하므로)

| 클라이언트 | 방법 | 이 저장소에서 확인한 범위 |
|---|---|---|
| Claude Code | `claude mcp add --scope user basic-memory -- /ABSOLUTE/PATH/basic-memory mcp --project ai-vault` | 문법은 `claude mcp add --help` 기준이며 **실행하지 않음**. `~/.claude.json`은 앱이 계속 다시 쓰는 상태 파일이라 `merge_mcp_config.py`는 이 파일의 적용을 거부함 |
| Codex | `codex mcp add basic-memory -- /ABSOLUTE/PATH/basic-memory mcp --project ai-vault` 또는 아래 병합 도구 | 문법은 `codex mcp add --help` 기준이며 실행하지 않음. 공식 명령은 [예시](../examples/codex-mcp.toml)의 타임아웃 값(120초)을 넣지 않으므로 필요하면 `config.toml`에 추가 |
| Claude Desktop | 설정 JSON에 병합 (macOS 경로: `~/Library/Application Support/Claude/claude_desktop_config.json`) | 병합 도구는 임시 파일로 검증. 다른 OS의 경로는 확인하지 않았으니 앱 문서를 확인 |
| ChatGPT·dots | [설정 방법](setup.md)의 터널 절차 | 이 작업에서는 재검증하지 않음 |

### 설정 파일 병합 도구 (미리보기 → 적용)

기존 설정을 덮어쓰지 않고 `basic-memory` 항목만 추가함. 먼저 **미리보기**만 실행됨 (파일 변경 없음)

```sh
python3 scripts/merge_mcp_config.py --format codex-toml \
  --target "$HOME/.codex/config.toml" \
  --command "$(command -v basic-memory)" --project ai-vault
```

변경 내용이 맞으면 같은 명령에 `--apply`를 붙임. 변경 후 내용이 올바른 파일인지 먼저 검증하고, `.bak-타임스탬프` 백업을 만든 뒤 임시 파일에 써서 교체하고, 다시 읽어 확인함. 같은 명령을 반복해도 안전함 (이미 같으면 변경 없음). 해석할 수 없거나 구조가 예상과 다른 파일은 수정하지 않고 멈춤
Claude Desktop은 `--format claude-json`에 위 경로를 `--target`으로 지정함

설정을 반영하려면 클라이언트를 재시작하거나 새 채팅을 엶. 설정 파일이 맞는 것과 채팅에서 도구가 보이는 것은 별개임

## 5. 첫 기록 (연결 시험)

새 채팅에서 [연결 시험 문구](../prompts/roundtrip-test.md)를 그대로 보냄. 기대 결과: README 읽기 → 한글 검색 → 시험 노트에 표식 1회 기록 → 재조회로 확인

### 처음 검색이 0건일 때

원인이 두 가지일 수 있음 (둘 다 격리 환경에서 재현함)

1. **색인 전**: 새로 등록한 폴더는 색인되기 전까지 읽기·쓰기는 되어도 검색이 비어 있을 수 있음 → `basic-memory reindex --project ai-vault --full`을 한 번 실행하고 다시 검색
2. **기본(hybrid) 검색이 임베딩 모델을 못 써서 비어 있음**: 이 버전은 의미 검색 구성요소가 있으면 기본 검색을 hybrid로 하고, 임베딩 모델을 받지 못한 환경(오프라인·차단)에서는 **텍스트 색인이 있어도 결과가 0건**이었음. 텍스트(`text`) 검색은 같은 조건에서 한글도 정상이었음 → 검색할 때 `search_type="text"`를 지정하거나, 환경변수 `BASIC_MEMORY_DEFAULT_SEARCH_TYPE=text`로 기본값을 바꿈 (환경변수는 CLI에서 확인함. 설정 파일의 `default_search_type`은 코드에 있으나 실행하지 않음)

임베딩에 관한 사실: 기본 설정은 로컬 실행(fastembed)이며 모델 이름이 `bge-small-en-v1.5`(영어 모델 이름)임. 첫 실행 때 모델 파일을 Hugging Face에서 내려받음. 노트 내용을 외부로 보내는지는 네트워크 트래픽을 측정하지 않아 확인하지 못했고, 기본 provider가 로컬이라는 설정만 확인함. 한글 의미 검색의 품질은 평가하지 않았음 (5개 노트의 데모에서는 관련 노트가 1순위였으나 표본이 작음)
이 저장소의 현재 요약 검색 예시는 처음부터 `search_type: text`를 쓰므로 이 문제의 영향을 받지 않음 ([노트 구조](context-structure.md))

## 6. 평소 사용

[평소 사용하는 방법](usage.md)의 문구로 재개·저장·인계를 요청함. 공통 지침은 [prompts/shared-context.md](../prompts/shared-context.md)
수정 전에는 대상 노트가 실제로 있는지 먼저 읽어 확인함 — 없는 노트에 `append`하면 오류 없이 새 노트가 만들어지고, 편집 실패는 `isError` 없이 응답 본문(`# Edit Failed`)으로 옴 ([오류 대응](troubleshooting.md))

## 7. 문제가 생기면

[오류 대응](troubleshooting.md) → 해결되지 않으면 `vault_doctor.py`를 다시 실행해 설정 불일치부터 제거함
설치가 잘 됐는지 격리된 임시 환경에서 재현해 보려면 `python3 scripts/demo_roundtrip.py` (실제 설정·Vault를 건드리지 않음)
