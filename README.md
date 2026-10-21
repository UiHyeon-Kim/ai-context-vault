# AI Context Vault

여러 AI(ChatGPT, Codex, Claude 등)가 **같은 Markdown 노트를 읽고 써서 작업 맥락을 이어 가게 하는 설정·운영 starter kit**

개인 노트 백업 저장소가 아니다. 연결 설정 예시, 기록 규칙, 인계 양식, 설치 점검 도구, 가상 데모 Vault를 담았다

## 무엇인가

AI는 대화가 끝나면 맥락을 잃고, 다른 AI는 그 대화를 모른다. 이 구성은 중요한 결정·근거·남은 일을 **노트로 저장**하고 다음 AI가 **그 노트를 다시 읽게** 한다. 전체 대화를 실시간으로 복제하지는 않는다

### 직접 만든 것과 외부 도구

| 구분 | 내용 |
|---|---|
| **외부 도구 (이 저장소가 만들지 않음)** | [Basic Memory](https://docs.basicmemory.com/) — 노트 색인·검색·읽기·쓰기 MCP 도구 제공 (AGPL-3.0-or-later). Obsidian, OpenAI tunnel-client |
| **이 저장소가 만든 것** | ① 현재 요약 / 상세 이력 / 인계 기록 구조와 양식 ② AI 공통 지침 ③ 설정 예시 ④ `vault_doctor.py` 사전 검사 ⑤ `merge_mcp_config.py` 안전한 설정 병합 ⑥ 가상 데모 Vault와 재현 시험 스크립트 |

새 메모리 제품, MCP 서버, 검색 엔진, 동기화 서비스를 만든 것이 아니다. 자세한 분류는 [기능 상태와 책임 구분](docs/status.md)

## 누구에게 필요한가

- Codex·Claude Code·ChatGPT 등을 번갈아 쓰며 “아까 정한 것”을 매번 다시 설명하는 사람
- 결정과 근거를 노트로 남기고 AI가 이어서 읽게 하고 싶은 사람 (Obsidian 사용 여부는 무관)
- 필요 없는 것: 클라우드 가입, 별도 서버, 데이터베이스 운영 (로컬 Basic Memory 사용)

## 빠른 시작

자세한 단계는 [빠른 시작](docs/quickstart.md). 요약

```sh
# 1. Basic Memory 설치 후 (공식 안내 참고), Vault 등록
basic-memory project add ai-vault /ABSOLUTE/PATH/AI-Vault --local

# 2. 사전 검사 (읽기 전용)
python3 scripts/vault_doctor.py --vault /ABSOLUTE/PATH/AI-Vault --project ai-vault

# 3. 클라이언트 설정에 병합 — 기본은 미리보기, 맞으면 --apply (백업 자동 생성, 반복 실행 안전)
python3 scripts/merge_mcp_config.py --format codex-toml --target "$HOME/.codex/config.toml" \
  --command "$(command -v basic-memory)" --project ai-vault
```

스크립트는 **Python 3.11 이상**이 필요하다 (macOS 기본 `/usr/bin/python3`는 3.9라 안내 메시지를 내고 멈춘다)
Claude Code는 `claude mcp add --scope user …`, Codex는 `codex mcp add …` 공식 명령도 쓸 수 있다 — 클라이언트별 방법은 [빠른 시작](docs/quickstart.md#4-ai-클라이언트에-연결)

그다음 새 채팅에서 [연결 시험 문구](prompts/roundtrip-test.md)로 읽기 → 검색 → 기록 → 재조회를 확인한다
먼저 연습하려면 [데모 Vault](examples/demo-vault/README.md)를 복사해 등록한다 (가상 데이터)

> 지원 환경: macOS에서 직접 검증(Basic Memory 0.22.1). Windows·Linux는 단위 테스트만 GitHub Actions로 확인했고 Basic Memory 연동·실사용은 **미검증**

## 사용 예시

작업 시작·재개

> AI-Vault(`ai-vault`)의 README를 먼저 읽고, Sample Notes App의 현재 요약부터 찾아 읽어줘. 상세 이력은 근거가 필요할 때만. 확정한 결정과 남은 일을 정리한 뒤 이어서 진행해줘

결정 저장

> 방금 확정한 결정·이유·보류 범위를 해당 현재 요약에 갱신하고, 사용자 결정과 AI 제안을 구별해줘. 마지막 수정 후 다시 읽어 저장을 확인해줘

실제로 이렇게 기록된 모습은 [데모 현재 요약](examples/demo-vault/Projects/Sample-Notes-App.md)에서 볼 수 있다 — 현재 상태(구현/빌드/설치/실사용 구분), 사용자 결정과 AI 제안, 확인된 사실과 추정, 보류·금지 범위가 나뉘어 있다. 더 많은 문구는 [평소 사용하는 방법](docs/usage.md)

## 설정

| 무엇 | 어디에 |
|---|---|
| 이름(표시 이름 / 프로젝트 ID / 폴더 / 저장소)의 차이 | [이름 구분](docs/naming.md) — 문서는 표시 이름으로 `AI-Vault`를 씀. 짧게 바꾸고 싶으면 표시 이름만 바꾸고 ID `ai-vault`는 유지하길 권장 |
| 로컬 MCP, ChatGPT 터널, 자동 실행 | [설정 방법](docs/setup.md) |
| 예시 파일 | [`examples/`](examples) — `/ABSOLUTE/PATH`, `REPLACE_WITH_TUNNEL_ID`는 반드시 바꿔야 함. `vault_doctor.py`가 남은 자리 표시자를 찾아 준다 |
| 백업·복구·업데이트·제거 | [유지보수](docs/maintenance.md) |
| 노트 구조 | [현재 요약과 상세 이력](docs/context-structure.md), 양식은 [`templates/`](templates) |

## 문제 해결

[오류 대응](docs/troubleshooting.md): 검색 0건, 도구 오류, 쓰기 응답 손실 후 저장 여부 확인(재조회 전에는 같은 쓰기를 반복하지 않음)
설정이 의심되면 `vault_doctor.py`를 먼저 실행한다

## 검증 현황

| 검증 | 결과 |
|---|---|
| 단위 테스트 `python3 -m unittest discover -s tests` | 34개 통과 (macOS: Python 3.11·3.12·3.14·3.15) |
| GitHub Actions 단위 테스트 (`.github/workflows/ci.yml`) | Ubuntu·Windows × Python 3.11·3.13, 4개 잡 모두 통과 (2026-10-22 첫 실행) |
| 격리 환경 재현 `python3 scripts/demo_roundtrip.py` | 15/15 — 등록, 사전 검사, 한글 검색, 현재 요약/이력 필터, 읽기, 작성·수정·재조회, 백업 리허설 |
| 네트워크 차단 시뮬레이션 `--offline` | 14 통과 + 경고 1 (기본 hybrid 검색이 0건, 텍스트 검색은 정상) |
| MCP stdio 계층 `python3 scripts/mcp_stdio_check.py` | 11/11 |
| 실제 설정·Vault 읽기 전용 점검 `vault_doctor.py` | 오류 0건 (수정 없음) |
| 실제 ChatGPT/Codex/Claude 채팅 연결 | 2026-10 개인 환경 기록만 있음 ([검증 현황](docs/verification.md)) |

“MCP 호출이 된다”와 “채팅 속 AI가 지침을 따른다”는 서로 다른 검증이며, 후자는 이번 도구들로 보장하지 않는다

## 한계

- 전체 대화를 동기화하지 않는다. **저장한 노트만** 공유된다
- AI가 지침을 항상 따른다는 보장이 없다. 중요한 인계는 저장 위치를 명시하고 재조회로 확인한다
- 쓰기 안전은 서버 기능이 아니라 운영 규칙이다 — 확인 없는 `append` 반복은 중복되고, 없는 노트에 `append`하면 오류 없이 새 노트가 만들어지며, 편집 실패가 `isError` 없이 올 수 있다 (모두 시험으로 확인)
- 새 Vault는 색인 전 검색이 비어 있을 수 있다. 첫 실행에서 Basic Memory가 임베딩 모델을 내려받으며, 받지 못하면 기본(hybrid) 검색이 비므로 `search_type=text`를 쓴다
- ChatGPT·dots 사용 시 Vault가 있는 컴퓨터가 켜져 있고 터널이 동작해야 한다. 요금·플랜은 각 서비스 기준이다
- 코드·ADR·백로그의 정본은 각 프로젝트 저장소다. Vault에는 요약과 링크만 둔다

## 라이선스

[MIT](LICENSE) — 이 저장소의 파일에만 적용된다. Basic Memory(AGPL-3.0-or-later), OpenAI tunnel-client, Obsidian은 각자의 라이선스를 따르며 포함하지 않는다. 선택 근거는 [라이선스 선택과 근거](docs/license-options.md)

## 문서 목록

[빠른 시작](docs/quickstart.md) · [이름 구분](docs/naming.md) · [설정](docs/setup.md) · [사용법](docs/usage.md) · [노트 구조](docs/context-structure.md) · [오류 대응](docs/troubleshooting.md) · [유지보수](docs/maintenance.md) · [기능 상태](docs/status.md) · [검증 현황](docs/verification.md) · [라이선스](docs/license-options.md)
[공통 지침](prompts/shared-context.md) · [연결 시험](prompts/roundtrip-test.md) · [인계 양식](templates/handoff.md) · [이력 양식](templates/history.md) · [Vault README 양식](templates/vault-readme.md)

## 이 저장소에 넣지 않는 것

개인 노트 본문, 채팅 내보내기, 실행 로그, 인증 키, 실제 터널 ID와 사용자별 설정은 포함하지 않는다
`.gitignore`는 실수 방지용이므로 올리기 전 실제 변경사항을 확인한다 (`vault_doctor.py`의 비밀값 검사도 보조로 쓸 수 있다)
2026-10-06 개인 Vault 정리용 일회성 스크립트와 백업도 포함하지 않는다

## 공식 참고 자료

- [Basic Memory 로컬 설치](https://docs.basicmemory.com/start-here/quickstart-local)
- [Basic Memory와 Obsidian](https://docs.basicmemory.com/integrations/obsidian/)
- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [ChatGPT 플러그인 연결](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [dots 컴퓨터·앱 연결](https://learn.chatgpt.com/docs/dots/computers-and-apps)
- [dots 작업·기억](https://learn.chatgpt.com/docs/dots/tasks-and-memory)
