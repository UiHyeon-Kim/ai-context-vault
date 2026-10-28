#!/usr/bin/env python3
"""데모 Vault로 처음 쓰는 사람의 흐름을 격리 환경에서 재현한다 (Python 3.11+).

설치된 basic-memory CLI(`basic-memory tool ...`)만 사용하고, 임시 폴더에
(HOME, BASIC_MEMORY_CONFIG_DIR, Vault 사본)를 만들어 실제 설정·Vault를 건드리지 않는다.
이 검사는 'Basic Memory 도구 계층'의 동작 확인이며 ChatGPT/Claude/Codex 채팅에서
AI가 지침을 따르는지는 검증하지 않는다.

    python3 scripts/demo_roundtrip.py [--binary basic-memory] [--keep] [--offline]

--offline: 임베딩 모델을 받을 수 없는 환경을 흉내낸다(HF_HUB_OFFLINE=1).
  이때 텍스트 검색은 통과해야 하고 기본(hybrid) 검색은 WARN이 정상이다.
호출자의 BASIC_MEMORY_* 환경변수는 지우고 실행한다(예: 기본 검색 유형을 text로 바꿔 둔 환경에서도 hybrid 단계가 그대로 시험된다).
참고: 첫 실행에서 Basic Memory가 의미 검색용 임베딩 모델을 Hugging Face에서 내려받는다
(격리 HOME이라 매 실행마다 다시 받으므로 수십 초 걸린다).
종료 코드: FAIL이 하나라도 있으면 1, WARN은 실패가 아니다.
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    sys.exit(f"Python 3.11 이상이 필요합니다 (현재 {sys.version.split()[0]}). `python3 --version`으로 확인하세요.")

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = "demo-vault"
MARK = "RT-MARK-7f3a"  # 시험용 고유 표식 (실제 노트에 쓰지 말 것)
NOTE = "Inbox/데모 테스트 노트"
HISTORY_TITLE = "2026-01-05-검색-검증"


def isolated_env(cfg: Path, home: Path, offline: bool = False) -> dict:
    """'격리' 실행용 환경. 호출자의 BASIC_MEMORY_*(기본 검색 유형, 홈 폴더 등)와 HF_HUB_OFFLINE을 지워
    사용자 설정이 시험 결과에 섞이지 않게 하고, 임시 HOME·설정 폴더만 가리키게 한다."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("BASIC_MEMORY_") and k != "HF_HUB_OFFLINE"}
    env.update(HOME=str(home), USERPROFILE=str(home), BASIC_MEMORY_CONFIG_DIR=str(cfg), PYTHONIOENCODING="utf-8")
    if offline:
        env["HF_HUB_OFFLINE"] = "1"
    return env


def reindex_outcome(returncode: int, stdout: str) -> tuple[bool, str]:
    """`reindex --full` 결과 판정. 임베딩 모델을 받지 못하면 Basic Memory 0.22.1은 종료 코드 0으로,
    0.23.x는 'Reindex failed'와 함께 0이 아닌 코드로 끝나지만 텍스트 색인은 모두 만들어진다.
    텍스트 색인이 완료됐으면 통과로 보고 임베딩 실패는 설명에 적는다(기본 검색 단계가 따로 확인한다)."""
    low = stdout.lower()
    text_done = "full-text search index rebuilt" in low
    emb_failed = bool(re.search(r"\b[1-9]\d* errors\b", stdout)) or "reindex failed" in low
    if emb_failed:
        return text_done, (f"텍스트 색인 완료, 임베딩 실패(모델을 받지 못한 환경일 수 있음, 종료 코드 {returncode})" if text_done
                           else f"텍스트 색인이 만들어지지 않음(종료 코드 {returncode})")
    return returncode == 0, "텍스트·임베딩 색인 완료" if returncode == 0 else f"색인 실패(종료 코드 {returncode})"


def parse_json(stdout: str):
    i = stdout.find("{")
    try:
        return json.loads(stdout[i:]) if i >= 0 else {}
    except ValueError:
        return {}


def body(proc) -> str:
    """read-note 출력(JSON, \\uXXXX 이스케이프)에서 본문만 꺼낸다. 한글 비교는 반드시 파싱 후에 한다."""
    return parse_json(proc.stdout).get("content", "")


def titles(proc) -> list[str]:
    return [x.get("title", "") for x in parse_json(proc.stdout).get("results", [])]


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--binary", default="basic-memory")
    ap.add_argument("--keep", action="store_true", help="임시 폴더를 지우지 않고 경로를 출력")
    ap.add_argument("--offline", action="store_true", help="임베딩 모델을 받을 수 없는 환경을 흉내냄")
    a = ap.parse_args(argv)
    exe = shutil.which(a.binary) or a.binary

    tmp = Path(tempfile.mkdtemp(prefix="aicv-demo-"))
    vault, cfg, home, backup = tmp / "vault", tmp / "cfg", tmp / "home", tmp / "backup"
    shutil.copytree(ROOT / "examples" / "demo-vault", vault)
    home.mkdir()
    env = isolated_env(cfg, home, a.offline)
    results: list[tuple[str, str]] = []

    def run(*args: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([exe, *args], env={**env, **(extra_env or {})}, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=600)

    def tool(name: str, *args: str, search_type: str | None = None) -> subprocess.CompletedProcess:
        extra = {"BASIC_MEMORY_DEFAULT_SEARCH_TYPE": search_type} if search_type else None
        return run("tool", name, "--project", PROJECT, "--local", *args, extra_env=extra)

    def step(name: str, ok: bool, detail: str = "", warn_if_not: bool = False) -> None:
        status = "PASS" if ok else ("WARN" if warn_if_not else "FAIL")
        results.append((name, status))
        print(f"[{status}] {len(results)}. {name}" + (f" — {detail}" if detail else ""))

    try:
        r = run("project", "add", PROJECT, str(vault), "--local")
        step("프로젝트 등록(임시 설정)", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:])
        d = subprocess.run([sys.executable, str(ROOT / "scripts" / "vault_doctor.py"), "--vault", str(vault), "--project", PROJECT,
                            "--binary", exe, "--config-dir", str(cfg)], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        step("vault_doctor 사전 검사", d.returncode == 0, "오류 0건" if d.returncode == 0 else d.stdout[-300:])

        ri = run("reindex", "--project", PROJECT, "--full")  # CLI 단독 사용 시 색인을 먼저 만들어야 검색됨
        ok, detail = reindex_outcome(ri.returncode, ri.stdout)
        step("색인(reindex --full)", ok, detail)

        t1 = titles(tool("search-notes", "클라우드", search_type="text"))
        step("한글 텍스트 검색 '클라우드' → 해당 노트만", t1 == ["Sample-Notes-App"], f"결과 {t1}")
        t2 = titles(tool("search-notes", "동기", search_type="text"))
        step("한글 접두어 검색 '동기' → '동기화' 포함 노트", {"Sample-Notes-App", "오프라인-동기화-조사"} <= set(t2), f"결과 {t2}")

        cur = titles(tool("search-notes", "Sample", "--meta", "context_role=current", search_type="text"))
        step("현재 요약 필터(context_role=current): 요약은 나오고 이력은 제외", "Sample-Notes-App" in cur and HISTORY_TITLE not in cur, f"결과 {cur}")
        hist = titles(tool("search-notes", "--meta", "context_role=history", search_type="text"))
        step("이력 필터(context_role=history): 이력만", hist == [HISTORY_TITLE], f"결과 {hist}")

        dflt = titles(tool("search-notes", "동기화"))  # 기본 검색 = 의미 검색이 켜져 있으면 hybrid
        step("기본(hybrid) 검색 결과 있음", bool(dflt), f"결과 {len(dflt)}건" if dflt else "0건 — 임베딩을 쓸 수 없으면 비는 것이 정상. search_type=text로 대체",
             warn_if_not=True)

        rd = tool("read-note", "Projects/Sample-Notes-App")
        step("노트 읽기(현재 요약: 현재 상태·보류·금지·사실/추정 구분)", all(k in body(rd) for k in ("현재 상태", "보류·금지 범위", "확인된 사실 / 추정")))

        w = tool("write-note", "--title", "데모 테스트 노트", "--folder", "Inbox", "--content", f"# 테스트\n\n최초 본문 {MARK}-A 백업리허설\n")
        rd = tool("read-note", NOTE)
        step("테스트 노트 작성 후 재조회", w.returncode == 0 and body(rd).count(f"{MARK}-A") == 1)

        e = tool("edit-note", NOTE, "--operation", "append", "--content", f"\n수정 내용 {MARK}-B\n")
        rd = tool("read-note", NOTE)
        step("수정(append) 후 재조회 — 기존 내용 보존", e.returncode == 0 and body(rd).count(f"{MARK}-B") == 1 and body(rd).count(f"{MARK}-A") == 1)

        # 같은 append를 확인 없이 반복하면 중복된다 → 문서의 '재조회 후 쓰기' 규칙의 근거
        tool("edit-note", NOTE, "--operation", "append", "--content", f"\n수정 내용 {MARK}-B\n")
        n = body(tool("read-note", NOTE)).count(f"{MARK}-B")
        step("확인 없는 append 반복은 중복됨(예상된 동작)", n == 2, f"표식 {n}회 → 재조회 후 이미 있으면 쓰지 않아야 함")

        f = tool("edit-note", NOTE, "--operation", "find_replace", "--find-text", "존재하지 않는 문구", "--content", "x")
        step("없는 문자열의 find_replace는 오류로 중단됨", f.returncode != 0 and "not found" in (f.stdout + f.stderr))

        note_file = vault / "Inbox" / "데모 테스트 노트.md"
        on_disk = note_file.read_text(encoding="utf-8")
        step("디스크의 Markdown 파일과 일치", f"{MARK}-A" in on_disk and f"{MARK}-B" in on_disk)

        # 백업·복구 리허설: Vault 폴더 복사 → 노트 삭제 → 색인 갱신 → 복구 → 색인 갱신
        shutil.copytree(vault, backup)
        note_file.unlink()
        run("reindex", "--project", PROJECT, "--search", "--full")
        gone = titles(tool("search-notes", "백업리허설", search_type="text"))
        shutil.copy2(backup / "Inbox" / "데모 테스트 노트.md", note_file)
        run("reindex", "--project", PROJECT, "--search", "--full")
        back = titles(tool("search-notes", "백업리허설", search_type="text"))
        step("백업 리허설: 삭제 시 검색에서 사라지고, 복구 후 reindex로 다시 검색됨", gone == [] and back == ["데모 테스트 노트"], f"삭제 후 {gone} / 복구 후 {back}")
    finally:
        if a.keep:
            print(f"임시 폴더 유지: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    bad = [n for n, s in results if s == "FAIL"]
    warn = [n for n, s in results if s == "WARN"]
    passed = sum(1 for _, s in results if s == "PASS")
    print(f"\n통과 {passed} / 경고 {len(warn)} / 실패 {len(bad)} (총 {len(results)})" + (f"\n실패: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
