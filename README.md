# AI Context Vault

Obsidian의 Markdown 노트를 Basic Memory MCP로 연결해 ChatGPT, dots, Codex, Claude 사이에서 저장된 작업 맥락을 이어 쓰는 구성 예시

개인 Vault의 백업 저장소가 아니라, 연결 설정 예시와 사용법을 보관하는 저장소다

## 어떻게 동작하나

1. AI가 공용 Vault의 운영 규칙과 관련 노트를 읽음
2. 대화에서 확정한 결정·이유·근거·남은 일을 해당 노트에 기록함
3. 다른 AI가 같은 노트의 최신 내용을 읽고 작업을 이어감

전체 대화를 실시간 복제하지 않으며, 저장하지 않은 내용을 다른 AI가 알고 있다고 가정하지 않음
특정 개발 프로젝트를 먼저 만들 필요는 없음 — `ai-vault`는 공용 보관함 이름이며 조사·학습·개인 결정에도 사용 가능

```text
Codex / Claude Code / Claude Desktop ── 로컬 MCP ─┐
                                                ├─ Basic Memory ─ Obsidian Vault
ChatGPT / dots ─ AI-Vault 플러그인 ─ 보안 터널 ───┘
```

## 먼저 볼 문서

- [평소 사용하는 방법](docs/usage.md): 재개·기획 저장·조사·인계 요청 예시
- [설정 방법](docs/setup.md): 로컬 MCP와 ChatGPT 터널 연결
- [검증 현황](docs/verification.md): 실제 채팅 검증과 남은 범위
- [공통 지침 예시](prompts/shared-context.md): 각 AI에 적용할 공용 기록 원칙
- [연결 시험 문구](prompts/roundtrip-test.md): 읽기 → 검색 → 기록 → 재조회
- [인계 노트 양식](templates/handoff.md): 결정 이유와 미완료 상태를 보존하는 형식

## 운영 조건

- 로컬 Basic Memory를 사용하는 구성으로 별도 Basic Memory Cloud 가입은 하지 않음
- 사용하는 AI 서비스의 요금·플랜·사용량 제한은 별개
- ChatGPT와 dots가 로컬 Vault를 사용하려면 Mac이 켜져 있고 깨어 있으며 터널이 동작해야 함
- dots의 자체 기억과 AI-Vault는 별개이며, 여러 AI에 전달할 결과는 Vault에 명시적으로 저장해야 함
- 코드·ADR·백로그의 정본은 각 프로젝트 저장소에 유지하고 Vault에는 요약과 링크만 남김

## 이 저장소에 넣지 않는 것

개인 노트 본문, 채팅 내보내기, 실행 로그, 인증 키, 실제 터널 ID와 사용자별 설정은 포함하지 않음
예시의 `/ABSOLUTE/PATH`와 `REPLACE_WITH_TUNNEL_ID`는 자신의 환경에서 바꿔야 하는 자리 표시자임
`.gitignore`는 실수 방지용이며 업로드 전 실제 변경사항도 확인해야 함

## 공식 참고 자료

- [Basic Memory 로컬 설치](https://docs.basicmemory.com/start-here/quickstart-local)
- [Basic Memory와 Obsidian](https://docs.basicmemory.com/integrations/obsidian/)
- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [ChatGPT 플러그인 연결](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [dots 컴퓨터·앱 연결](https://learn.chatgpt.com/docs/dots/computers-and-apps)
- [dots 작업·기억](https://learn.chatgpt.com/docs/dots/tasks-and-memory)
