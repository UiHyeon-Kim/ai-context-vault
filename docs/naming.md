# 이름 구분: 표시 이름 · 프로젝트 ID · 폴더 · 저장소

같은 대상을 부르는 이름이 네 종류라 설정 오류가 자주 생김. 어떤 이름이 어디에 쓰이는지 구별함

| 이름 | 예시(기본값) | 쓰이는 곳 | 바꿔도 되나 |
|---|---|---|---|
| 앱 표시 이름 | `AI-Vault` (ChatGPT 플러그인·커넥터 이름) | 사람이 보는 목록. AI에게 “~에서 읽어줘”라고 말할 때의 호칭 | 자유롭게 가능 (예: `Vault`). 설정 파일에는 영향 없음 |
| Basic Memory 프로젝트 ID | `ai-vault` | `--project ai-vault`(MCP 설정, 터널 프로필), 도구 호출의 `project` 인자, 공통 지침 | 가능하지만 **한꺼번에 여러 곳**을 고쳐야 함 |
| Vault 폴더명 | `AI-Vault/` | 디스크의 Markdown 폴더. `project add <ID> <폴더>`로 ID와 연결 | 폴더를 옮기면 프로젝트 등록 경로를 다시 맞춰야 함 |
| 저장소 이름 | `ai-context-vault` | GitHub의 이 starter kit | 위 세 가지와 무관 |

## 권장

- 이 저장소의 문서는 표시 이름으로 `AI-Vault`를 씀. `Vault` 같은 짧은 이름이 필요하면 **표시 이름만** 바꾸고(플러그인·커넥터 목록), **프로젝트 ID와 폴더명은 기본값을 유지**함. 이유: 표시 이름은 한 곳(플러그인 목록)에서만 쓰이지만 ID는 설정 파일·프롬프트·터널 프로필·노트 링크에 흩어져 있음
- AI에게 말할 때는 표시 이름과 프로젝트 ID를 함께 적으면 도구가 헷갈리지 않음: “AI-Vault(`ai-vault`)에서 …” (표시 이름을 바꿨다면 바꾼 이름으로)

## ID를 바꾸면 영향받는 곳

실제로 확인한 사실: Basic Memory의 permalink는 프로젝트 ID로 시작함 (데모에서 `demo-vault/projects/sample-notes-app`). 그러므로 ID를 바꾸면 permalink로 건 링크·참조가 달라질 수 있음

체크리스트
1. Basic Memory 프로젝트 등록 (`basic-memory project list`로 현재 ID 확인)
2. Codex·Claude MCP 설정의 `args` (`--project`)
3. 터널 프로필의 `mcp.commands[].command`
4. 공통 지침과 Vault README에 적은 프로젝트 ID
5. 다른 노트가 permalink로 참조하는지 검색

`python3 scripts/vault_doctor.py --project <ID> ...`가 설정 파일의 `--project` 값과 등록된 ID가 서로 다른 경우를 잡아 줌

## 폴더명과 한글

폴더명·노트 제목에 한글을 써도 동작함 (데모로 확인). 단 permalink는 로마자로 변환되어 읽기 어려워질 수 있으므로 링크는 가능하면 제목이나 `폴더/제목` 경로로 지정함
