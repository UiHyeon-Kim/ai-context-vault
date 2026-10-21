#!/usr/bin/env python3
"""설치 전후 사전 검사 (읽기 전용). 표준 라이브러리만 사용 (Python 3.11+).

    python3 scripts/vault_doctor.py --vault /path/to/Vault [--project ai-vault] \
        [--config examples/claude-mcp.json ...] [--config-dir DIR]

--config에는 MCP 설정(JSON/TOML), 터널 프로필(JSON), LaunchAgent plist를 줄 수 있다.
검사만 하고 아무것도 수정·실행하지 않는다 (basic-memory는 --version만 호출).
키 파일은 존재와 권한만 보고 내용은 읽지 않으며, 비밀값처럼 보이는 문자열은 값 없이 위치·종류만 알린다.
종료 코드: 0 = 오류 없음(경고 가능), 1 = 오류 있음.
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    sys.exit(f"Python 3.11 이상이 필요합니다 (현재 {sys.version.split()[0]}). `python3 --version`으로 확인하고 3.11 이상 인터프리터로 실행하세요.")

import argparse
import json
import os
import plistlib
import re
import shlex
import shutil
import subprocess
import tomllib
from pathlib import Path

PLACEHOLDERS = ("/ABSOLUTE/PATH", "REPLACE_WITH", "C:\\ABSOLUTE")
# 값은 출력하지 않고 종류와 위치만 보고한다.
SECRET_PATTERNS = {
    "OpenAI/Anthropic 형식 키": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "GitHub 토큰": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS 액세스 키": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "개인 키 블록": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
SKIP_DIRS = {".git", ".obsidian", ".basic-memory", "node_modules"}
SCAN_SUFFIXES = {".md", ".json", ".toml", ".yaml", ".yml", ".txt", ".plist"}
MAX_CONTEXT_SCAN = 2000


class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0

    def ok(self, msg: str) -> None:
        print(f"[ OK ] {msg}")

    def warn(self, msg: str) -> None:
        self.warnings += 1
        print(f"[WARN] {msg}")

    def err(self, msg: str) -> None:
        self.errors += 1
        print(f"[FAIL] {msg}")


def check_binary(r: Report, binary: str) -> None:
    exe = shutil.which(binary) or (binary if Path(binary).is_file() else None)
    if not exe:
        r.err(f"'{binary}' 실행 파일을 찾을 수 없음. Basic Memory를 설치하거나 --binary로 절대 경로를 지정")
        return
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        text = (out.stdout or out.stderr).strip().splitlines()
        r.ok(f"{exe}: {text[0] if text else '버전 출력 없음'}")
    except (OSError, subprocess.TimeoutExpired) as e:
        r.err(f"{exe} --version 실행 실패: {type(e).__name__}")


def _front_value(path: Path, key: str) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    m = re.search(rf"^{re.escape(key)}:\s*(\S+)", text.split("\n---", 1)[0], re.M)
    return m.group(1) if m else None


def check_vault(r: Report, vault: Path) -> None:
    if not vault.is_dir():
        r.err(f"Vault 폴더가 없음: {vault}")
        return
    r.ok(f"Vault 폴더 확인: {vault}")
    if (vault / "README.md").is_file():
        r.ok("README.md 있음 (AI가 처음 읽는 운영 규칙)")
    else:
        r.warn("Vault에 README.md가 없음. templates/vault-readme.md를 참고해 만들기")
    md = [p for p in vault.rglob("*.md") if not set(p.relative_to(vault).parts) & SKIP_DIRS]
    r.ok(f"Markdown 노트 {len(md)}개")
    if md and not any(_front_value(p, "context_role") for p in md[:MAX_CONTEXT_SCAN]):
        r.warn("context_role 메타데이터가 있는 노트가 없음. 현재 요약 필터 검색은 결과가 비어 있을 수 있음 (필터 없는 검색으로 대체 가능)")


def scan_secrets(r: Report, vault: Path, extra: list[Path]) -> None:
    hits = 0
    files = [p for p in vault.rglob("*") if p.is_file() and p.suffix in SCAN_SUFFIXES
             and not set(p.relative_to(vault).parts) & SKIP_DIRS] if vault.is_dir() else []
    for p in files + extra:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for kind, rx in SECRET_PATTERNS.items():
            if rx.search(text):
                hits += 1
                r.warn(f"비밀값처럼 보이는 {kind}: {p} (값은 출력하지 않음). 공개 저장소에 올리기 전에 제거")
    if not hits:
        r.ok("비밀값 패턴 없음 (정규식 기반의 간이 검사이며 완전한 검사가 아님)")


def _exists_unless_placeholder(path_str: str) -> bool:
    return any(p in path_str for p in PLACEHOLDERS) or Path(path_str).is_file() or bool(shutil.which(path_str))


def _check_command(r: Report, name: str, cmd: str, args: list, project: str) -> None:
    if not cmd:
        r.err(f"{name}: command 누락")
    elif not _exists_unless_placeholder(cmd):
        r.err(f"{name}: command 경로가 존재하지 않음: {cmd}")
    if "--project" not in args:
        r.warn(f"{name}: args에 --project가 없음 (기본 프로젝트가 사용됨)")
    else:
        got = args[args.index("--project") + 1:][:1]
        if got != [project]:
            r.err(f"{name}: --project 값이 '{project}'와 다름: {got}")


def _check_parent_dir(r: Report, name: str, label: str, value: object) -> None:
    if isinstance(value, str) and value and not any(p in value for p in PLACEHOLDERS) and not Path(value).parent.is_dir():
        r.warn(f"{name}: {label}의 상위 폴더가 없음 → 실행 전에 만들어 둘 것: {Path(value).parent}")


def _check_mcp_servers(r: Report, name: str, data: object, key: str, project: str) -> None:
    servers = data.get(key) if isinstance(data, dict) else None
    server = servers.get("basic-memory") if isinstance(servers, dict) else None
    if not isinstance(server, dict):
        r.err(f"{name}: basic-memory 서버 항목이 없음 (찾은 위치: {key}). 프로젝트별(local) 범위에만 등록됐다면 이 검사는 찾지 못함")
        return
    args = server.get("args", [])
    _check_command(r, name, server.get("command", ""), args if isinstance(args, list) else [], project)


def _check_tunnel(r: Report, name: str, data: dict, project: str) -> None:
    cp = data.get("control_plane") if isinstance(data.get("control_plane"), dict) else {}
    if not cp.get("tunnel_id"):
        r.err(f"{name}: control_plane.tunnel_id 누락")
    key = cp.get("api_key", "")
    if isinstance(key, str) and key.startswith("file:"):
        kp = Path(key[5:])
        if any(p in key for p in PLACEHOLDERS):
            pass  # 자리 표시자는 아래 공통 검사가 보고함
        elif not kp.is_file():
            r.err(f"{name}: api_key 파일이 없음: {kp}")
        elif os.name == "posix" and kp.stat().st_mode & 0o077:
            r.warn(f"{name}: 키 파일 권한이 넓음(소유자만 읽기·쓰기 0600 권장): {kp}")
    elif key:
        r.warn(f"{name}: api_key가 file: 참조가 아님. 키 값이 설정 파일에 직접 들어 있다면 공개 저장소에 올리지 말 것(값은 출력하지 않음)")
    else:
        r.err(f"{name}: control_plane.api_key 누락")
    cmds = data.get("mcp", {}).get("commands", []) if isinstance(data.get("mcp"), dict) else []
    if not cmds:
        r.err(f"{name}: mcp.commands 누락")
    for c in cmds if isinstance(cmds, list) else []:
        line = c.get("command", "") if isinstance(c, dict) else ""
        parts = shlex.split(line, posix=(os.name != "nt")) if line else []
        _check_command(r, name, parts[0] if parts else "", parts[1:], project)
    _check_parent_dir(r, name, "log.file", (data.get("log") or {}).get("file"))
    _check_parent_dir(r, name, "health.url_file", (data.get("health") or {}).get("url_file"))


def _check_plist(r: Report, name: str, data: dict) -> None:
    prog = data.get("ProgramArguments") or []
    if not prog:
        r.err(f"{name}: ProgramArguments 누락")
    elif not _exists_unless_placeholder(str(prog[0])):
        r.err(f"{name}: 실행 파일이 존재하지 않음: {prog[0]}")
    wd = data.get("WorkingDirectory")
    if isinstance(wd, str) and not any(p in wd for p in PLACEHOLDERS) and not Path(wd).is_dir():
        r.err(f"{name}: WorkingDirectory가 존재하지 않음: {wd}")
    for k in ("StandardOutPath", "StandardErrorPath"):
        _check_parent_dir(r, name, k, data.get(k))


def check_config(r: Report, path: Path, project: str) -> None:
    if not path.is_file():
        r.err(f"설정 파일이 없음: {path}")
        return
    name = path.name
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    left = [p for p in PLACEHOLDERS if p in text]
    try:
        if path.suffix == ".plist":
            data, kind = plistlib.loads(raw), "plist"
        elif path.suffix == ".toml":
            data, kind = tomllib.loads(raw.decode("utf-8-sig")), "mcp-toml"
        else:
            data = json.loads(raw.decode("utf-8-sig"))
            kind = "tunnel" if isinstance(data, dict) and "control_plane" in data else "mcp-json"
    except Exception as e:  # noqa: BLE001 - 형식별로 예외 종류가 달라 한 곳에서 사용자 메시지로 바꾼다
        hint = " (YAML은 JSON과 호환되는 형식일 때만 검사할 수 있음)" if path.suffix in {".yaml", ".yml"} else ""
        r.err(f"{name}: 문법 오류 ({type(e).__name__}){hint}")
        return
    r.ok(f"{name}: 문법 정상 ({kind})")
    if left:
        r.err(f"{name}: 자리 표시자가 남아 있음 {left} → 실제 값으로 교체 필요")
    if kind == "mcp-toml":
        _check_mcp_servers(r, name, data, "mcp_servers", project)
    elif kind == "mcp-json":
        _check_mcp_servers(r, name, data, "mcpServers", project)
    elif kind == "tunnel":
        _check_tunnel(r, name, data, project)
    else:
        _check_plist(r, name, data if isinstance(data, dict) else {})


def check_registered(r: Report, project: str, vault: Path, config_dir: str | None) -> None:
    """프로젝트 등록 여부를 Basic Memory의 config.json에서 읽기 전용으로 확인한다."""
    base = Path(config_dir or os.environ.get("BASIC_MEMORY_CONFIG_DIR") or Path.home() / ".basic-memory")
    cfg = base / "config.json"
    if not cfg.is_file():
        r.warn(f"Basic Memory 설정을 찾을 수 없음({cfg}). 아직 project add 전이면 정상")
        return
    try:
        projects = json.loads(cfg.read_text(encoding="utf-8")).get("projects", {})
    except ValueError:
        r.err(f"{cfg}: JSON을 읽을 수 없음")
        return
    entry = projects.get(project)
    if entry is None:
        r.err(f"프로젝트 ID '{project}'가 Basic Memory에 등록되지 않음. 등록된 ID: {sorted(projects)}")
    elif Path(entry.get("path", "")).resolve() != vault.resolve():
        r.err(f"프로젝트 '{project}'가 다른 폴더를 가리킴: {entry.get('path')} ≠ {vault}")
    else:
        r.ok(f"프로젝트 '{project}' → Vault 폴더 일치")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # 비 UTF-8 콘솔에서도 한글 출력이 깨지지 않게 (Windows는 미검증)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", required=True, type=Path, help="Vault(Markdown 폴더) 경로")
    ap.add_argument("--project", default="ai-vault", help="Basic Memory 프로젝트 ID (기본: ai-vault)")
    ap.add_argument("--binary", default="basic-memory", help="basic-memory 실행 파일 이름 또는 경로")
    ap.add_argument("--config", action="append", default=[], type=Path, help="검사할 설정 파일(MCP JSON/TOML, 터널 프로필, plist), 여러 번 지정 가능")
    ap.add_argument("--config-dir", help="Basic Memory 설정 폴더 (기본: BASIC_MEMORY_CONFIG_DIR 또는 ~/.basic-memory)")
    a = ap.parse_args(argv)
    r = Report()
    check_binary(r, a.binary)
    check_vault(r, a.vault)
    check_registered(r, a.project, a.vault, a.config_dir)
    for c in a.config:
        check_config(r, c, a.project)
    scan_secrets(r, a.vault, a.config)
    print(f"\n오류 {r.errors}건, 경고 {r.warnings}건. 이 검사는 설정·파일 상태만 보며 MCP 호출이나 채팅에서의 AI 동작은 검증하지 않음")
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
