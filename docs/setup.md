# 연결 설정 예시

검증 환경은 macOS, Basic Memory 0.22.1, tunnel-client 0.0.15였음
아래는 기존 정상 구성을 옮기기 위한 예시이며 다른 OS·버전에서 자동 설치까지 검증한 패키지가 아님
기존 사용자 설정 파일을 예시 파일로 통째로 덮어쓰지 않고 필요한 항목만 병합함

## 로컬 Vault와 Basic Memory

1. Obsidian Vault를 만들거나 기존 Vault 경로를 확인함
2. [Basic Memory 공식 안내](https://docs.basicmemory.com/start-here/quickstart-local)에 따라 설치함
3. 아직 등록하지 않은 Vault만 프로젝트로 추가함

```sh
basic-memory project add ai-vault /ABSOLUTE/PATH/AI-Vault --local
```

`ai-vault`는 개발 저장소가 아닌 Basic Memory 보관함 식별자임
기존 노트가 있다면 먼저 백업하고, 자동 frontmatter·permalink·포맷 변경 설정은 원하는 운영 방식에 맞게 확인함
Vault의 README에 폴더 책임, 정본 위치, 출처·검증 규칙을 둠

## Codex·Claude 로컬 MCP

- Codex는 [TOML 예시](../examples/codex-mcp.toml)를 기존 설정에 병합함
- Claude 계열은 [stdio JSON 예시](../examples/claude-mcp.json)를 해당 클라이언트의 지원 설정 방식에 맞게 적용함
- 실행 파일 경로는 실제 설치 위치의 절대 경로를 사용함
- `mcp --project ai-vault`로 연결할 보관함 범위를 지정함
- 설정을 저장한 뒤 클라이언트에서 연결을 다시 불러오거나 새 채팅을 열어 도구 노출을 확인함

설정 파일이 존재하는 것과 실제 채팅에서 도구가 동작하는 것은 다름
[연결 시험](../prompts/roundtrip-test.md)을 각각의 클라이언트에서 실행함

## ChatGPT 웹·dots용 터널

로컬 stdio 서버를 OpenAI Secure MCP Tunnel로 연결하고 ChatGPT의 사용자 지정 플러그인으로 등록하는 구성임

1. [공식 터널 문서](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)에서 현재 설치·권한 절차를 확인함
2. Platform에서 대상 조직·ChatGPT 워크스페이스에 터널을 만듦
3. 필요한 최소 런타임 권한만 가진 키를 비공개 파일로 보관함
4. [프로필 예시](../examples/tunnel-profile.json)의 절대 경로와 터널 ID를 로컬 사본에서 바꿈
5. tunnel-client를 실행하고 health와 control-plane poll 성공을 확인함
6. [ChatGPT 연결 절차](https://developers.openai.com/plugins/deploy/connect-chatgpt)에 따라 해당 터널을 사용하는 AI-Vault 플러그인을 등록함
7. ChatGPT와 dots 각각에서 실제 읽기·검색·기록·재조회를 시험함

프로필은 키 값 대신 `file:` 참조를 사용함
키 파일 권한은 0600, 상위 디렉터리는 0700으로 관리하며 GitHub에 포함하지 않음
로컬 stdio 서버에 별도 OAuth가 없다는 의미의 ‘인증 없음’과 OpenAI 터널의 인증은 구별함

```sh
tunnel-client run \
  --profile-dir /ABSOLUTE/PATH/profiles \
  --profile ai-vault \
  --pid.file /ABSOLUTE/PATH/ai-vault.pid
```

예시 JSON은 YAML로도 읽을 수 있는 형식이며 로컬 프로필 이름은 `ai-vault.yaml`로 둠
로그·health·PID 파일의 상위 디렉터리는 실행 전에 준비함

## Mac 로그인 자동 실행

[LaunchAgent 예시](../examples/com.example.ai-vault-tunnel.plist)의 모든 절대 경로를 바꾸고 사용자 `~/Library/LaunchAgents/` 아래에 설치함
plist 안의 `~`나 `$HOME`은 셸처럼 자동 확장되지 않으므로 실제 절대 경로가 필요함
다른 방식으로 같은 터널을 이미 실행 중이라면 정상 종료하고 하나의 실행 방식만 사용함

```sh
plutil -lint "$HOME/Library/LaunchAgents/com.example.ai-vault-tunnel.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.example.ai-vault-tunnel.plist"
launchctl print "gui/$(id -u)/com.example.ai-vault-tunnel"
```

`RunAtLoad`는 로그인 시 시작, `KeepAlive`는 종료 후 재실행을 담당함
실제 재부팅·로그인 후 동작은 자신의 환경에서 확인해야 함

```sh
tunnel-client health \
  --url-file /ABSOLUTE/PATH/ai-vault.url \
  --pid-file /ABSOLUTE/PATH/ai-vault.pid \
  --require-control-plane-poll --json
```

시작 직후에는 첫 poll 전이라 마지막 조건이 아직 충족되지 않을 수 있음
Mac이 꺼지거나 잠들면 로컬 Vault 접근도 사용할 수 없을 수 있음
dots에 컴퓨터 전체 접근 권한을 별도로 주는 것과 이 MCP 터널 연결은 다른 기능임
