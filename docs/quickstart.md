# 빠른 시작: 설치부터 첫 기록까지

**폴더 등록 → AI 연결 → 규칙 등록 → 저장 확인** 순서로 진행합니다.
아래 명령은 macOS의 zsh·bash 기준입니다. Windows·Linux의 실제 앱 연결은 미검증입니다. [환경별 확인 범위](status.md#지원-환경)

## 0. 준비물

| 준비물 | 확인 방법 |
|---|---|
| Python 3.12 이상 | `python3 --version` |
| [Basic Memory 설치](https://docs.basicmemory.com/start-here/quickstart-local) | `basic-memory --version` |
| Markdown 폴더 | 새 폴더 또는 Obsidian Vault |

**기존 노트를 사용한다면 먼저 [백업](maintenance.md)하세요.**

<details>
<summary>Python·Basic Memory 버전 설명</summary>

- Basic Memory는 Python 3.12 이상, 이 저장소의 보조 스크립트는 Python 3.11 이상이 필요합니다.
- `python3`가 구버전이면 설치된 최신 인터프리터(예: `python3.12`)로 명령을 실행하세요.
- 현재 격리 호환성 검증 버전은 Basic Memory 1.0.0입니다. 0.22.1은 이전 설치·CI 검증 버전입니다.
- 버전 고정 설치 예시: `uv tool install basic-memory==1.0.0` 또는 `pip install basic-memory==1.0.0`. 이번 1.0 시험은 이미 설치된 패키지로 진행했으며 새 설치 명령 자체는 실행하지 않았습니다.

[버전별 검증 결과](basic-memory-compatibility.md)

</details>

## 1. 폴더 등록

프로젝트 ID는 기본 `ai-vault`를 사용합니다. 아래 경로를 실제 폴더 경로로 바꾸세요.

```sh
basic-memory project add ai-vault /ABSOLUTE/PATH/AI-Vault --local
```

부르기 쉬운 호칭은 4단계에서 고릅니다. 실제 ID·폴더명과의 차이는 [이름 안내](naming.md)를 참고하세요.

<details>
<summary>개인 노트 대신 데모로 연습하기</summary>

원본을 수정하지 않도록 [가상 데모 Vault](../examples/demo-vault/README.md)를 복사해서 사용합니다. `/tmp/demo-vault`는 예시 경로이며 기존 폴더와 겹치지 않게 정하세요.

```sh
cp -R examples/demo-vault /tmp/demo-vault
basic-memory project add demo-vault /tmp/demo-vault --local
```

데모를 골랐다면 이후 명령의 경로와 프로젝트 ID도 데모 값으로 바꾸세요.

</details>

## 2. 연결 전 검사

```sh
python3 scripts/vault_doctor.py --vault /ABSOLUTE/PATH/AI-Vault --project ai-vault
```

`[FAIL]`이 있으면 안내에 따라 수정한 뒤 다시 실행하세요. 이 검사는 읽기 전용입니다.

<details>
<summary>무엇을 검사하나요?</summary>

실행 파일, 폴더와 README, 등록된 프로젝트 경로, 비밀값처럼 보이는 문자열을 검사합니다. 값은 출력하지 않습니다.
AI 설정 파일을 만든 뒤에는 `--config 파일경로`를 붙여 다시 검사할 수 있습니다. MCP 설정·터널 프로필·LaunchAgent plist를 지원합니다.

</details>

## 3. 사용할 AI 연결

**사용할 앱 하나만 골라** 해당 부분을 펼치세요. `/ABSOLUTE/PATH/basic-memory`는 설치된 실행 파일 경로로 바꿉니다.
아래 Codex·Claude 등록 명령은 도움말 기준 예시이며 실행 검증한 명령은 아닙니다.

<details>
<summary>Codex</summary>

```sh
codex mcp add basic-memory -- /ABSOLUTE/PATH/basic-memory mcp --project ai-vault
```

시작 시간이 부족하면 [설정 예시](../examples/codex-mcp.toml)의 타임아웃을 참고하세요. `mcp add` 도움말에는 타임아웃 옵션이 없어 직접 추가가 필요할 수 있습니다(실행 결과 미확인).

</details>

<details>
<summary>Claude Code</summary>

```sh
claude mcp add --scope user basic-memory -- /ABSOLUTE/PATH/basic-memory mcp --project ai-vault
```

`~/.claude.json`은 앱이 관리하는 상태 파일입니다. 아래 병합 도구로 직접 수정하지 마세요.

</details>

<details>
<summary>Claude Desktop</summary>

설정 JSON의 `mcpServers`에 [연결 예시](../examples/claude-mcp.json)를 기존 내용을 보존하며 반영합니다.
macOS 경로는 `~/Library/Application Support/Claude/claude_desktop_config.json`입니다. 다른 OS는 앱 문서에서 경로를 확인하세요.
아래 병합 도구를 사용한다면 `--format claude-json`과 이 경로를 지정합니다.

</details>

<details>
<summary>ChatGPT·dots</summary>

[원격 연결 안내](setup.md)의 터널 절차를 따르세요. 이번 수정에서는 원격 연결을 재검증하지 않았습니다.

</details>

<details>
<summary>대안: 설정 파일 병합 도구 사용하기</summary>


기존 설정을 덮어쓰지 않고 `basic-memory` 항목만 추가함. 먼저 **미리보기**만 실행됨 (파일 변경 없음)

```sh
python3 scripts/merge_mcp_config.py --format codex-toml \
  --target "$HOME/.codex/config.toml" \
  --command "$(command -v basic-memory)" --project ai-vault
```

변경 내용이 맞으면 같은 명령에 `--apply`를 붙임. 변경 후 내용이 올바른 파일인지 먼저 검증하고, `.bak-타임스탬프` 백업을 만든 뒤 임시 파일에 써서 교체하고, 다시 읽어 확인함. 같은 명령을 반복해도 안전함 (이미 같으면 변경 없음). 해석할 수 없거나 구조가 예상과 다른 파일은 수정하지 않고 멈춤
Claude Desktop은 `--format claude-json`에 위 경로를 `--target`으로 지정함

설정을 반영하려면 클라이언트를 재시작하거나 새 채팅을 엶. 설정 파일이 맞는 것과 채팅에서 도구가 보이는 것은 별개임

</details>

연결 설정 후 앱을 재시작하거나 새 채팅을 열어 도구가 보이는지 확인하세요.

## 4. 이름·저장 규칙 등록

[초기 설정 안내](agent-setup.md)에 따라 스킬을 설치하거나 파일을 읽게 한 뒤 요청합니다.

> Vault 초기 설정해줘. 이 프로젝트에서 ai-vault를 사용하고, 호칭은 내 메모장, 저장은 요청할 때만 해줘.

## 5. 첫 기록 확인

새 채팅에 [연결 시험 문구](../prompts/roundtrip-test.md)를 보내세요.
**README 읽기 → 검색 → 표식 1회 저장 → 재조회**까지 확인하면 됩니다.

검색이 비거나 임베딩 오류가 나면 텍스트 검색으로 다시 찾으세요. 1.0은 `mode=text`, 0.x는 `search_type=text`입니다.

<details>
<summary>검색이 안 될 때의 원인·버전별 동작</summary>


아래 설명은 Basic Memory 0.x에서 관찰한 동작임. 1.0은 등록 시 색인을 기다리며, 검색 인자는 `mode=text`·`filters`를 사용함. 임베딩 오류와 버전별 차이는 [1.0 호환성 검증](basic-memory-compatibility.md)을 참고함

원인이 두 가지일 수 있음 (둘 다 격리 환경에서 재현함)

1. **색인 전**: 새로 등록한 폴더는 색인되기 전까지 읽기·쓰기는 되어도 검색이 비어 있을 수 있음 → `basic-memory reindex --project ai-vault --full`을 한 번 실행하고 다시 검색
2. **기본(hybrid) 검색이 임베딩 모델을 못 써서 비어 있음**: 이 버전은 의미 검색 구성요소가 있으면 기본 검색을 hybrid로 하고, 임베딩 모델을 받지 못한 환경(오프라인·차단)에서는 **텍스트 색인이 있어도 결과가 0건**이었음. 텍스트(`text`) 검색은 같은 조건에서 한글도 정상이었음 → 검색할 때 `search_type="text"`를 지정하거나, 환경변수 `BASIC_MEMORY_DEFAULT_SEARCH_TYPE=text`로 기본값을 바꿈. 환경변수는 CLI에서만 확인했음. MCP 서버로 실행될 때는 셸 환경변수를 물려받지 못할 수 있으므로 클라이언트의 MCP 서버 설정 `env`에 넣어야 함 (`codex mcp add --env KEY=VALUE`, Claude 설정 JSON의 `env` 키 — 이 경로는 실행하지 않아 미확인). 설정 파일의 `default_search_type`은 코드에 있으나 실행하지 않음

임베딩에 관한 사실: 기본 설정은 로컬 실행(fastembed)이며 모델 이름이 `bge-small-en-v1.5`(영어 모델 이름)임. 첫 실행 때 모델 파일을 Hugging Face에서 내려받음. 노트 내용을 외부로 보내는지는 네트워크 트래픽을 측정하지 않아 확인하지 못했고, 기본 provider가 로컬이라는 설정만 확인함. 한글 의미 검색의 품질은 평가하지 않았음 (5개 노트의 데모에서는 관련 노트가 1순위였으나 표본이 작음)
이 저장소의 현재 요약 검색 예시는 처음부터 텍스트 검색(1.0: `mode: text`, 0.x: `search_type: text`)을 쓰므로 이 문제의 영향을 받지 않음 ([노트 구조](context-structure.md))

</details>

이제 **“내 메모장에 기록해줘”**처럼 [짧게 요청](usage.md)할 수 있습니다.
문제가 남으면 [오류 대응](troubleshooting.md)을 확인하세요. 수정 전 기존 노트 조회와 저장 후 재조회는 항상 필요합니다.

<details>
<summary>실제 설정을 건드리지 않고 도구 계층 시험하기</summary>

```sh
python3 scripts/demo_roundtrip.py --offline
```

임시 Vault·설정·DB를 사용하고 종료 시 정리합니다. 임베딩을 받을 수 없는 조건이라 기본 검색 경고가 날 수 있습니다. [시험 범위](basic-memory-compatibility.md)

</details>
