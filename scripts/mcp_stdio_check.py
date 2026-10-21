#!/usr/bin/env python3
"""실제 MCP(stdio) 계층 확인: 서버를 띄우고 클라이언트처럼 도구 목록 → 검색 → 읽기 → 쓰기 → 재조회를 호출한다.

`mcp` 패키지가 필요하다. Basic Memory가 이미 의존하므로, 현재 Python에 없으면
basic-memory 실행 파일의 shebang이 가리키는 Python(uv/pipx 설치 기준)으로 자동 재실행한다.
찾지 못하면 그 Python을 직접 지정해 실행한다:  <basic-memory의 python> scripts/mcp_stdio_check.py

격리: 임시 HOME / BASIC_MEMORY_CONFIG_DIR / Vault 사본만 쓰고 호출자의 BASIC_MEMORY_* 환경변수는 지운다. 실제 설정은 읽지도 쓰지도 않는다.
문서화된 현재 요약 검색 레시피(search_type=text, metadata_filters, page_size=3)도 여기서 확인한다.
이것은 'MCP 호출이 된다'는 확인이며 채팅 속 AI가 지침을 따르는지는 별개다.
종료 코드: FAIL이 있으면 1, 2는 mcp를 쓸 수 없음. WARN(기본 검색이 빈 경우)은 실패가 아니다.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = "demo-vault"
MARK = "MCP-MARK-91c2"
HISTORY_TITLE = "2026-01-05-검색-검증"


def isolated_env(cfg: Path, home: Path) -> dict:
    """'격리' 실행용 환경. 호출자의 BASIC_MEMORY_*·HF_HUB_OFFLINE을 지우고 임시 HOME·설정 폴더만 가리키게 한다."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("BASIC_MEMORY_") and k != "HF_HUB_OFFLINE"}
    env.update(HOME=str(home), USERPROFILE=str(home), BASIC_MEMORY_CONFIG_DIR=str(cfg), PYTHONIOENCODING="utf-8")
    return env


def find_basic_memory_python() -> str | None:
    exe = shutil.which("basic-memory")
    if not exe:
        return None
    try:
        first = Path(exe).resolve().read_text(encoding="utf-8", errors="ignore").splitlines()[0]
    except (OSError, IndexError):
        return None
    if first.startswith("#!"):
        parts = first[2:].strip().split()
        if parts and Path(parts[0]).is_file():
            return parts[0]
    return None


def text_of(result) -> str:
    return "".join(getattr(c, "text", "") for c in result.content)


def titles_of(result) -> list[str]:
    try:
        return [x.get("title", "") for x in json.loads(text_of(result)).get("results", [])]
    except ValueError:
        return []


async def run_checks() -> int:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    exe = shutil.which("basic-memory") or "basic-memory"
    tmp = Path(tempfile.mkdtemp(prefix="aicv-mcp-"))
    results: list[str] = []

    def step(name, ok, detail="", warn_if_not=False):
        status = "PASS" if ok else ("WARN" if warn_if_not else "FAIL")
        results.append(status)
        print(f"[{status}] {len(results)}. {name}" + (f" — {detail}" if detail else ""))

    try:
        vault, cfg, home = tmp / "vault", tmp / "cfg", tmp / "home"
        shutil.copytree(ROOT / "examples" / "demo-vault", vault)
        home.mkdir()
        env = isolated_env(cfg, home)
        subprocess.run([exe, "project", "add", PROJECT, str(vault), "--local"], env=env, capture_output=True, check=True)
        subprocess.run([exe, "reindex", "--project", PROJECT, "--full"], env=env, capture_output=True)
        params = StdioServerParameters(command=exe, args=["mcp", "--project", PROJECT], env=env)
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                names = {t.name for t in (await s.list_tools()).tools}
                need = {"search_notes", "read_note", "write_note", "edit_note"}
                step("도구 목록 노출", need <= names, f"필수 4종 {'모두 있음' if need <= names else '누락: ' + str(need - names)} / 전체 {len(names)}개")

                async def call(tool, args):
                    return await s.call_tool(tool, {**args, "project": PROJECT})

                t = titles_of(await call("search_notes", {"query": "클라우드", "search_type": "text", "output_format": "json"}))
                step("한글 텍스트 검색 '클라우드' → 해당 노트만", t == ["Sample-Notes-App"], f"결과 {t}")
                t = titles_of(await call("search_notes", {"query": "Sample", "search_type": "text", "page_size": 3,
                                                          "metadata_filters": {"context_role": "current"}, "output_format": "json"}))
                step("문서화된 레시피(text + context_role=current + page_size=3): 요약 포함·이력 제외·3건 이하",
                     "Sample-Notes-App" in t and HISTORY_TITLE not in t and len(t) <= 3, f"결과 {t}")
                t = titles_of(await call("search_notes", {"metadata_filters": {"context_role": "history"}, "output_format": "json"}))
                step("이력 필터(context_role=history): 이력만", t == [HISTORY_TITLE], f"결과 {t}")
                t = titles_of(await call("search_notes", {"query": "동기화", "output_format": "json"}))
                step("기본 검색(search_type 미지정, hybrid) 결과 있음", bool(t), f"{len(t)}건" if t else "0건 — 임베딩을 쓸 수 없는 환경이면 비는 것이 정상. search_type=text 사용",
                     warn_if_not=True)
                res = await call("read_note", {"identifier": "Projects/Sample-Notes-App"})
                step("현재 요약 읽기(현재 상태·보류·금지 범위)", all(k in text_of(res) for k in ("현재 상태", "보류·금지 범위")))
                await call("write_note", {"title": "MCP 테스트 노트", "directory": "Inbox", "content": f"# t\n\n본문 {MARK}-A\n"})
                res = await call("read_note", {"identifier": "Inbox/MCP 테스트 노트"})
                step("작성 후 재조회", text_of(res).count(f"{MARK}-A") == 1)
                await call("edit_note", {"identifier": "Inbox/MCP 테스트 노트", "operation": "append", "content": f"\n수정 {MARK}-B\n"})
                res = await call("read_note", {"identifier": "Inbox/MCP 테스트 노트"})
                tx = text_of(res)
                step("수정 후 재조회(기존 보존)", tx.count(f"{MARK}-A") == 1 and tx.count(f"{MARK}-B") == 1)
                res = await call("edit_note", {"identifier": "Inbox/MCP 테스트 노트", "operation": "find_replace",
                                               "find_text": "존재하지 않는 문구", "content": "x"})
                step("없는 문자열의 find_replace는 실패 응답(본문 'Edit Failed')", bool(res.isError) or "Edit Failed" in text_of(res),
                     f"isError={res.isError} — 0.22.1에서는 isError=False로 오므로 응답 본문과 재조회로 판단해야 함")
                res = await call("read_note", {"identifier": "Inbox/MCP 테스트 노트"})
                step("실패한 수정이 기존 내용을 바꾸지 않음", text_of(res).count(f"{MARK}-A") == 1 and text_of(res).count(f"{MARK}-B") == 1)
                # 알려진 주의 동작: 없는 노트에 append하면 오류 없이 새 노트가 만들어진다 (경로 오타가 조용히 새 노트가 됨)
                res = await call("edit_note", {"identifier": "Inbox/오타난-경로", "operation": "append", "content": "x"})
                made = await call("read_note", {"identifier": "Inbox/오타난-경로"})
                step("없는 노트에 append하면 새 노트가 만들어짐(주의: 먼저 존재 확인)", "Created note" in text_of(res) and "x" in text_of(made),
                     f"isError={res.isError}", warn_if_not=True)
    except Exception as e:  # noqa: BLE001 - 진단 출력용
        step("MCP 세션", False, f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n통과 {results.count('PASS')} / 경고 {results.count('WARN')} / 실패 {results.count('FAIL')} (총 {len(results)})")
    return 1 if "FAIL" in results else 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        import mcp  # noqa: F401
    except ImportError:
        py = find_basic_memory_python()
        if py and os.environ.get("AICV_REEXEC") != "1" and Path(py).resolve() != Path(sys.executable).resolve():
            print(f"현재 Python에 mcp가 없어 Basic Memory의 Python으로 다시 실행: {py}")
            return subprocess.call([py, __file__, *sys.argv[1:]], env={**os.environ, "AICV_REEXEC": "1"})
        print("mcp 패키지를 찾을 수 없음. Basic Memory가 설치된 Python으로 직접 실행하세요: <basic-memory의 python> scripts/mcp_stdio_check.py")
        return 2
    return asyncio.run(run_checks())


if __name__ == "__main__":
    sys.exit(main())
