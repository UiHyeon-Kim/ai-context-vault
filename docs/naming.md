# 부를 이름 바꾸기

AI에게 부르는 이름은 [초기 설정 스킬](../skills/vault-setup/SKILL.md)에서 선택함. 예를 들어 호칭 `내 메모장`을 프로젝트 `ai-vault`에 대응시키면 “내 메모장에 기록해줘”로 요청할 수 있음. 이후 호칭 변경도 같은 스킬에 요청함

현재 제공하는 것은 **호칭을 지침에 반영하는 스킬 절차**임. 임시 지침의 등록·이름 변경과 별도 문맥에서의 호칭 해석은 [행동 시험](setup-skill-verification.md)으로 확인했고, 실제 앱 자동 로드는 미검증임. 실제 프로젝트·폴더·앱 이름을 한꺼번에 바꾸는 자동화 도구는 없음

## 어떤 이름을 바꾸나요?

| 이름 | 예시(기본값) | 쓰이는 곳 | 바꿔도 되나 |
|---|---|---|---|
| AI에게 부를 호칭 | `Vault`, `내 메모장` | 상시 지침과 자연어 요청 | 초기 설정 스킬에서 선택·변경. 실제 연결 설정은 유지 |
| 앱 표시 이름 | `AI-Vault` (플러그인·커넥터 이름) | 사람이 보는 앱 목록 | 앱이 이름 변경을 지원할 때 해당 앱에서 별도 변경. 이 스킬은 변경하지 않음 |
| Basic Memory 프로젝트 ID | `ai-vault` | `--project ai-vault`(MCP 설정, 터널 프로필), 도구 호출의 `project` 인자, 공통 지침 | 가능하지만 **한꺼번에 여러 곳**을 고쳐야 함 |
| Vault 폴더명 | `AI-Vault/` | 디스크의 Markdown 폴더. `project add <ID> <폴더>`로 ID와 연결 | 폴더를 옮기면 프로젝트 등록 경로를 다시 맞춰야 함 |
| 저장소 이름 | `ai-context-vault` | GitHub의 이 starter kit | 위 세 가지와 무관 |

## 권장

- 단순히 부르기 쉬운 이름이 필요하면 **호칭만** 바꾸고 프로젝트 ID·폴더·앱 표시 이름은 유지함
- 지침에 호칭과 실제 프로젝트 대응을 한 번 저장하면 이후에는 짧은 호칭으로 요청함. 다른 AI에도 같은 대응을 적용해야 함
- 다른 프로젝트에 같은 호칭을 쓰면 모호하므로 구분할 이름을 선택함. 실제 ID·경로를 바꾸려는 요청은 호칭 변경과 구분함

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
