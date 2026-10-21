#!/usr/bin/env python3
"""기존 MCP 설정 파일에 basic-memory 항목만 병합한다. 표준 라이브러리만 사용 (Python 3.11+).

기본은 미리보기(dry-run)이며 --apply를 줄 때만 파일을 쓴다.
- 쓰기 전에 변경 후 내용이 올바른 JSON/TOML인지 먼저 검증하고, 아니면 아무것도 쓰지 않는다
- 같은 폴더에 타임스탬프 백업(.bak-YYYYmmdd-HHMMSS)을 만든 뒤 임시 파일에 써서 교체한다(원자적)
- 이미 같은 항목이 있으면 아무것도 하지 않아 반복 실행해도 안전하다
- 다른 값의 basic-memory 항목이 있으면 중단한다(JSON은 --replace로 교체 허용)
- ~/.claude.json은 Claude Code가 계속 기록하는 상태 파일이라 적용을 거부한다 → `claude mcp add` 사용

    python3 scripts/merge_mcp_config.py --format claude-json --target /path/to/claude_desktop_config.json \
        --command /abs/path/basic-memory --project ai-vault
    python3 scripts/merge_mcp_config.py --format codex-toml  --target ~/.codex/config.toml \
        --command /abs/path/basic-memory --project ai-vault --apply

복구: 백업 파일을 원래 이름으로 복사하면 된다.
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    sys.exit(f"Python 3.11 이상이 필요합니다 (현재 {sys.version.split()[0]}). `python3 --version`으로 확인하고 3.11 이상 인터프리터로 실행하세요.")

import argparse
import contextlib
import difflib
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import tomllib
from datetime import datetime
from pathlib import Path

NAME = "basic-memory"
# 실행 중인 앱이 수시로 다시 쓰는 상태 파일. 통째로 다시 쓰면 동시 기록을 덮어쓸 수 있다.
VOLATILE_FILES = {".claude.json"}  # 소문자로 비교


def desired(command: str, project: str, fmt: str) -> dict:
    entry: dict = {"command": command, "args": ["mcp", "--project", project]}
    if fmt == "codex-toml":
        entry.update(startup_timeout_sec=120, tool_timeout_sec=120)
    return entry


def toml_block(entry: dict) -> str:
    # json.dumps는 TOML 기본 문자열과 호환되는 이스케이프(\\, \")를 만든다.
    q = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731
    lines = [f"[mcp_servers.{NAME}]", f"command = {q(entry['command'])}",
             f"args = [{', '.join(q(x) for x in entry['args'])}]"]
    lines += [f"{k} = {entry[k]}" for k in ("startup_timeout_sec", "tool_timeout_sec") if k in entry]
    return "\n".join(lines) + "\n"


def describe(entry) -> str:
    """충돌 안내용 요약. command·args만 보여 주고 그 밖의 키(env, headers 등)는 값이 비밀일 수 있어 이름만 알린다."""
    if not isinstance(entry, dict):
        return f"({type(entry).__name__})"
    shown = {k: entry[k] for k in ("command", "args") if k in entry}
    hidden = sorted(k for k in entry if k not in ("command", "args"))
    return json.dumps(shown, ensure_ascii=False) + (f" + 값을 숨긴 키: {', '.join(hidden)}" if hidden else "")


def quote_for_shell(value: str) -> str:
    return subprocess.list2cmdline([value]) if os.name == "nt" else shlex.quote(value)


def parse(fmt: str, text: str) -> dict:
    """해석해서 dict를 돌려준다. 구조가 예상과 다르면 ValueError(깨끗한 메시지)."""
    if fmt == "claude-json":
        data = json.loads(text) if text.strip() else {}
        if not isinstance(data, dict):
            raise ValueError("최상위가 JSON 객체가 아님")
        if not isinstance(data.get("mcpServers", {}), dict):
            raise ValueError("mcpServers가 객체가 아님")
        return data
    data = tomllib.loads(text) if text.strip() else {}
    if not isinstance(data.get("mcp_servers", {}), dict):
        raise ValueError("mcp_servers가 표(table)가 아님")
    return data


def current_entry(fmt: str, data: dict):
    return data.get("mcpServers" if fmt == "claude-json" else "mcp_servers", {}).get(NAME)


def plan(fmt: str, text: str | None, entry: dict, replace: bool) -> tuple[str | None, str]:
    """(새 내용 또는 None, 상태 메시지). None이면 쓰지 않는다. 새 내용은 쓰기 전에 검증한다."""
    text = text or ""
    data = parse(fmt, text)
    cur = current_entry(fmt, data)
    if cur == entry:
        return None, "이미 동일한 항목이 있음. 변경 없음"
    if fmt == "claude-json":
        if cur is not None and not replace:
            raise SystemExit(f"중단: 다른 값의 '{NAME}' 항목이 이미 있음. 덮어쓰려면 --replace. 현재 값: {describe(cur)}")
        data.setdefault("mcpServers", {})[NAME] = entry
        new, status = json.dumps(data, indent=2, ensure_ascii=False) + "\n", ("항목 교체" if cur else "항목 추가")
    else:
        if cur is not None:
            raise SystemExit(f"중단: TOML에 다른 값의 [mcp_servers.{NAME}]이 있음. 주석·서식 보존을 위해 자동 교체하지 않으니 직접 수정. 현재 값: {describe(cur)}")
        sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        new, status = text + sep + toml_block(entry), "항목 추가 (기존 내용 뒤에 덧붙임)"
    # 쓰기 전 검증: 변경 후 내용이 유효하고 원하는 항목을 정확히 담아야 한다.
    try:
        ok = current_entry(fmt, parse(fmt, new)) == entry
    except ValueError as e:
        raise SystemExit(f"중단: 변경 후 내용이 올바른 파일이 아님({e}). 파일은 수정하지 않았음. 직접 편집하세요") from e
    if not ok:
        raise SystemExit("중단: 변경 후 내용에서 기대한 항목을 읽을 수 없음. 파일은 수정하지 않았음. 직접 편집하세요")
    return new, status


def unique_backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = path.with_name(f"{path.name}.bak-{stamp}")
    n = 1
    while bak.exists():
        bak = path.with_name(f"{path.name}.bak-{stamp}-{n}")
        n += 1
    return bak


class ChangedUnderUs(Exception):
    """읽은 뒤 교체 직전까지 다른 프로그램이 파일을 바꿨다."""


def atomic_write(path: Path, text: str, expect_old: bytes | None) -> None:
    """임시 파일에 쓴 뒤 교체한다. 교체 직전에 파일이 읽었을 때와 같은지(없었다면 여전히 없는지) 확인한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        if path.exists():
            shutil.copymode(path, tmp)
        if (path.read_bytes() if path.exists() else None) != expect_old:
            raise ChangedUnderUs
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows 등 비 UTF-8 콘솔에서도 한글이 깨지지 않게 (미검증 환경 대비)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", required=True, choices=["claude-json", "codex-toml"])
    ap.add_argument("--target", required=True, type=Path)
    ap.add_argument("--command", required=True, help="basic-memory 실행 파일의 절대 경로")
    ap.add_argument("--project", default="ai-vault")
    ap.add_argument("--apply", action="store_true", help="실제로 파일을 씀 (기본은 미리보기)")
    ap.add_argument("--replace", action="store_true", help="JSON의 기존 다른 항목을 교체 허용")
    ap.add_argument("--allow-missing-command", action="store_true", help="command 존재 검사를 건너뜀 (테스트용)")
    a = ap.parse_args(argv)

    cmd = Path(a.command)
    if not cmd.is_absolute():
        raise SystemExit("중단: --command는 절대 경로여야 함 (설정 파일은 셸처럼 PATH를 보장하지 않음)")
    if not a.allow_missing_command and not cmd.is_file():
        raise SystemExit(f"중단: 실행 파일이 없음: {cmd}")

    target = a.target.expanduser()
    real = target.resolve() if target.exists() else target  # 심볼릭 링크면 링크가 아닌 실제 파일을 갱신
    if {target.name.lower(), real.name.lower()} & VOLATILE_FILES:
        msg = (f"{real.name}은(는) Claude Code가 실행 중 계속 다시 쓰는 상태 파일이라 이 도구로 수정하지 않음. "
               f"대신 `claude mcp add --scope user {NAME} -- {quote_for_shell(a.command)} mcp --project {quote_for_shell(a.project)}` 를 사용 "
               "(문법은 `claude mcp add --help` 기준)")
        if a.apply:
            raise SystemExit("중단: " + msg)
        print("주의: " + msg)
    old_bytes = real.read_bytes() if real.exists() else None
    try:
        old = old_bytes.decode("utf-8-sig") if old_bytes is not None else None
    except UnicodeDecodeError as e:
        raise SystemExit(f"중단: 기존 파일이 UTF-8이 아님({e.reason}). 아무것도 수정하지 않음. UTF-8로 저장한 뒤 다시 실행하세요") from e
    crlf = bool(old and "\r\n" in old)
    old_lf = old.replace("\r\n", "\n") if old is not None else None
    try:
        new, status = plan(a.format, old_lf, desired(a.command, a.project, a.format), a.replace)
    except ValueError as e:
        raise SystemExit(f"중단: 기존 파일을 해석할 수 없음 ({e}). 아무것도 수정하지 않음") from e
    print(f"대상: {target}  →  {status}")
    if new is None:
        return 0
    sys.stdout.writelines(difflib.unified_diff((old_lf or "").splitlines(True), new.splitlines(True), "현재", "변경 후"))
    if a.format == "claude-json" and old:
        print("\n참고: JSON은 들여쓰기 2칸으로 다시 쓰이며 키 순서는 유지됨. 주석은 JSON에 없음")
    if not a.apply:
        print("\n미리보기만 수행함. 적용하려면 --apply")
        return 0
    if old is not None:
        bak = unique_backup(real)
        shutil.copy2(real, bak)
        print(f"백업: {bak}")
    try:
        atomic_write(real, new.replace("\n", "\r\n") if crlf else new, old_bytes)
    except ChangedUnderUs:
        raise SystemExit("중단: 읽은 뒤 파일이 바뀜(앱이 같은 파일을 쓰는 중일 수 있음). 파일은 수정하지 않았음. 앱을 종료하거나 잠시 뒤 다시 실행하세요 (백업은 이미 만들어졌을 수 있음)") from None
    again = real.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")  # 디스크에서 다시 읽어 확인
    ok = current_entry(a.format, parse(a.format, again)) == desired(a.command, a.project, a.format)
    print("적용 후 재조회: " + ("확인됨" if ok else "불일치! 백업에서 복구할 것"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
