"""표준 라이브러리 unittest. 실행: python3 -m unittest discover -s tests -v   (Python 3.11+)

basic-memory를 실행하지 않는 단위 테스트만 포함한다 (실제 호출 시험은 scripts/demo_roundtrip.py, scripts/mcp_stdio_check.py).
"""
import contextlib
import io
import json
import os
import plistlib
import re
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import merge_mcp_config as mc  # noqa: E402
import vault_doctor as vd  # noqa: E402

FAKE_BIN = sys.executable  # 모든 OS에 존재하는 절대 경로 실행 파일


def run_doctor(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = vd.main(list(args))
    return code, out.getvalue()


def tmpdir():
    d = tempfile.TemporaryDirectory()
    return d, Path(d.name)


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self._d, self.tmp = tmpdir()
        self.addCleanup(self._d.cleanup)
        self.vault = self.tmp / "vault"
        self.vault.mkdir()
        (self.vault / "README.md").write_text("# r\n", encoding="utf-8")
        self.cfgdir = self.tmp / "bm"
        self.cfgdir.mkdir()
        self.register("ai-vault", self.vault)

    def register(self, name, path):
        (self.cfgdir / "config.json").write_text(json.dumps({"projects": {name: {"path": str(path)}}}), encoding="utf-8")

    def doctor(self, *configs, binary=FAKE_BIN):
        args = ["--vault", str(self.vault), "--config-dir", str(self.cfgdir), "--binary", binary]
        for c in configs:
            args += ["--config", str(c)]
        return run_doctor(*args)

    def write_json(self, name, data):
        p = self.tmp / name
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def good_server(self, project="ai-vault"):
        return {"mcpServers": {"basic-memory": {"command": FAKE_BIN, "args": ["mcp", "--project", project]}}}

    def test_every_example_file_flags_placeholders(self):
        configs = [ROOT / "examples" / n for n in ("claude-mcp.json", "codex-mcp.toml", "tunnel-profile.json", "com.example.ai-vault-tunnel.plist")]
        code, out = run_doctor("--vault", str(self.vault), "--config-dir", str(self.cfgdir), *[x for c in configs for x in ("--config", str(c))])
        self.assertEqual(code, 1)
        self.assertEqual(out.count("자리 표시자가 남아 있음"), 4, out)

    def test_project_mismatch_and_missing_vault(self):
        self.register("ai-vault", self.tmp / "elsewhere")
        code, out = self.doctor()
        self.assertEqual(code, 1)
        self.assertIn("다른 폴더", out)
        code, out = run_doctor("--vault", str(self.tmp / "nope"), "--config-dir", str(self.cfgdir))
        self.assertIn("Vault 폴더가 없음", out)

    def test_clean_setup_passes(self):
        good = self.write_json("ok.json", self.good_server())
        code, out = self.doctor(good)
        self.assertEqual(code, 0, out)

    def test_wrong_project_arg_detected(self):
        bad = self.write_json("bad.json", self.good_server("other"))
        code, out = self.doctor(bad)
        self.assertEqual(code, 1)
        self.assertIn("--project 값이", out)

    def test_weird_json_shapes_do_not_crash(self):
        for name, data in {"list.json": [], "null.json": {"mcpServers": None}, "str.json": {"mcpServers": {"basic-memory": "x"}}}.items():
            code, out = self.doctor(self.write_json(name, data))
            self.assertEqual(code, 1, name)
            self.assertIn("basic-memory 서버 항목이 없음", out, name)

    def test_secret_scan_reports_location_not_value(self):
        secret = "sk-" + "a1B2c3D4" * 4
        (self.vault / "note.md").write_text(f"key: {secret}\n", encoding="utf-8")
        _, out = self.doctor()
        self.assertIn("note.md", out)
        self.assertNotIn(secret, out)

    def test_broken_json_config(self):
        broken = self.tmp / "b.json"
        broken.write_text("{bad", encoding="utf-8")
        code, out = self.doctor(broken)
        self.assertEqual(code, 1)
        self.assertIn("문법 오류", out)

    # --- 터널 프로필 / plist ---
    def tunnel_profile(self, **over):
        key = self.tmp / "runtime-api-key"
        key.write_text("dummy-not-a-secret", encoding="utf-8")
        os.chmod(key, 0o600)
        prof = {
            "control_plane": {"api_key": f"file:{key}", "base_url": "https://example.invalid", "tunnel_id": "abc123"},
            "health": {"url_file": str(self.tmp / "logs" / "h.url")},
            "log": {"file": str(self.tmp / "logs" / "t.log")},
            "mcp": {"commands": [{"channel": "main", "command": f"{FAKE_BIN} mcp --project ai-vault"}]},
        }
        (self.tmp / "logs").mkdir(exist_ok=True)
        prof.update(over)
        return self.write_json("profile.json", prof)

    def test_tunnel_profile_ok(self):
        code, out = self.doctor(self.tunnel_profile())
        self.assertEqual(code, 0, out)
        self.assertIn("(tunnel)", out)

    def test_tunnel_profile_problems(self):
        p = self.tunnel_profile()
        data = json.loads(p.read_text(encoding="utf-8"))
        data["control_plane"]["tunnel_id"] = ""
        data["control_plane"]["api_key"] = f"file:{self.tmp / 'missing-key'}"
        data["mcp"]["commands"][0]["command"] = f"{FAKE_BIN} mcp --project wrong"
        data["log"]["file"] = str(self.tmp / "no-such-dir" / "t.log")
        code, out = self.doctor(self.write_json("p2.json", data))
        self.assertEqual(code, 1)
        for needle in ("tunnel_id 누락", "api_key 파일이 없음", "--project 값이", "상위 폴더가 없음"):
            self.assertIn(needle, out)

    @unittest.skipUnless(os.name == "posix", "POSIX 권한 검사")
    def test_tunnel_key_permissions_warn_without_reading_key(self):
        p = self.tunnel_profile()
        key = Path(json.loads(p.read_text(encoding="utf-8"))["control_plane"]["api_key"][5:])
        os.chmod(key, 0o644)
        _, out = self.doctor(p)
        self.assertIn("권한이 넓음", out)
        self.assertNotIn("dummy-not-a-secret", out)

    def test_inline_api_key_warns_and_is_not_printed(self):
        p = self.tunnel_profile()
        data = json.loads(p.read_text(encoding="utf-8"))
        data["control_plane"]["api_key"] = "inline-dummy-value-123"
        _, out = self.doctor(self.write_json("p3.json", data))
        self.assertIn("file: 참조가 아님", out)
        self.assertNotIn("inline-dummy-value-123", out)

    def test_plist_checks(self):
        good = self.tmp / "a.plist"
        good.write_bytes(plistlib.dumps({"Label": "x", "ProgramArguments": [FAKE_BIN, "run"], "WorkingDirectory": str(self.tmp)}))
        self.assertEqual(self.doctor(good)[0], 0)
        bad = self.tmp / "b.plist"
        bad.write_bytes(plistlib.dumps({"Label": "x", "ProgramArguments": [str(self.tmp / "nope")], "WorkingDirectory": str(self.tmp / "nodir")}))
        code, out = self.doctor(bad)
        self.assertEqual(code, 1)
        self.assertIn("실행 파일이 존재하지 않음", out)
        self.assertIn("WorkingDirectory가 존재하지 않음", out)


class MergeTests(unittest.TestCase):
    def setUp(self):
        self._d, self.tmp = tmpdir()
        self.addCleanup(self._d.cleanup)

    def run_merge(self, fmt, target, *extra, project="ai-vault"):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mc.main(["--format", fmt, "--target", str(target), "--command", FAKE_BIN, "--project", project, *extra])
        return code, out.getvalue()

    def backups(self, name):
        return sorted(self.tmp.glob(f"{name}.bak-*"))

    def test_dry_run_does_not_write(self):
        t = self.tmp / "c.json"
        t.write_text('{"mcpServers": {"x": {"command": "y"}}}', encoding="utf-8")
        before = t.read_text(encoding="utf-8")
        self.run_merge("claude-json", t)
        self.assertEqual(t.read_text(encoding="utf-8"), before)
        self.assertEqual(self.backups("c.json"), [])

    def test_json_apply_preserves_other_keys_makes_backup_and_is_idempotent(self):
        t = self.tmp / "c.json"
        t.write_text('{"theme": "dark", "mcpServers": {"x": {"command": "y"}}}', encoding="utf-8")
        self.run_merge("claude-json", t, "--apply")
        data = json.loads(t.read_text(encoding="utf-8"))
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["mcpServers"]["x"], {"command": "y"})
        self.assertEqual(data["mcpServers"]["basic-memory"]["args"], ["mcp", "--project", "ai-vault"])
        self.assertEqual(len(self.backups("c.json")), 1)
        snapshot = t.read_text(encoding="utf-8")
        _, out = self.run_merge("claude-json", t, "--apply")
        self.assertIn("변경 없음", out)
        self.assertEqual(t.read_text(encoding="utf-8"), snapshot)
        self.assertEqual(len(self.backups("c.json")), 1)  # 재실행은 백업도 만들지 않음

    def test_restore_from_backup_is_byte_identical(self):
        t = self.tmp / "c.toml"
        original = '# 내 설정\nmodel = "x"\n[a]\nb = 1\n'.encode("utf-8")
        t.write_bytes(original)
        self.run_merge("codex-toml", t, "--apply")
        self.assertNotEqual(t.read_bytes(), original)
        t.write_bytes(self.backups("c.toml")[0].read_bytes())  # 문서의 복구 절차: 백업을 원래 이름으로 복사
        self.assertEqual(t.read_bytes(), original)

    def test_json_conflict_requires_replace(self):
        t = self.tmp / "c.json"
        t.write_text('{"mcpServers": {"basic-memory": {"command": "/old"}}}', encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.run_merge("claude-json", t, "--apply")
        self.assertIn("/old", t.read_text(encoding="utf-8"))
        self.run_merge("claude-json", t, "--apply", "--replace")
        self.assertEqual(json.loads(t.read_text(encoding="utf-8"))["mcpServers"]["basic-memory"]["command"], FAKE_BIN)

    def test_unparseable_or_odd_files_are_left_untouched_without_traceback(self):
        cases = {"broken.json": ("claude-json", "{bad"), "list.json": ("claude-json", "[]"),
                 "null.json": ("claude-json", '{"mcpServers": null}'), "inline.toml": ("codex-toml", 'mcp_servers = { other = { command = "x" } }\n')}
        for name, (fmt, content) in cases.items():
            t = self.tmp / name
            t.write_text(content, encoding="utf-8")
            with self.assertRaises(SystemExit) as cm:
                self.run_merge(fmt, t, "--apply")
            self.assertIn("중단", str(cm.exception), name)
            self.assertEqual(t.read_text(encoding="utf-8"), content, name)
            self.assertEqual(self.backups(name), [], name)
            self.assertEqual([p.name for p in self.tmp.glob(f"{name}.*.tmp")], [], name)  # 임시 파일 정리

    def test_toml_appends_keeps_comments_and_is_idempotent(self):
        t = self.tmp / "c.toml"
        t.write_text('# 내 설정\nmodel = "x"\n', encoding="utf-8")
        self.run_merge("codex-toml", t, "--apply")
        text = t.read_text(encoding="utf-8")
        self.assertTrue(text.startswith('# 내 설정\nmodel = "x"\n'))
        entry = tomllib.loads(text)["mcp_servers"]["basic-memory"]
        self.assertEqual(entry["args"], ["mcp", "--project", "ai-vault"])
        _, out = self.run_merge("codex-toml", t, "--apply")
        self.assertIn("변경 없음", out)
        self.assertEqual(t.read_text(encoding="utf-8"), text)

    def test_toml_windows_style_path_is_valid_toml(self):
        block = mc.toml_block(mc.desired(r"C:\Users\me\bin\basic-memory.exe", "ai-vault", "codex-toml"))
        self.assertEqual(tomllib.loads(block)["mcp_servers"]["basic-memory"]["command"], r"C:\Users\me\bin\basic-memory.exe")

    def test_new_file_and_relative_command_rejected(self):
        t = self.tmp / "new" / "c.toml"
        self.run_merge("codex-toml", t, "--apply")
        self.assertTrue(t.exists())
        with self.assertRaises(SystemExit):
            mc.main(["--format", "codex-toml", "--target", str(t), "--command", "basic-memory"])

    def test_claude_json_state_file_refuses_apply_but_allows_preview(self):
        t = self.tmp / ".claude.json"
        t.write_text("{}", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            self.run_merge("claude-json", t, "--apply")
        self.assertIn("claude mcp add", str(cm.exception))
        self.assertEqual(t.read_text(encoding="utf-8"), "{}")
        code, out = self.run_merge("claude-json", t)  # 미리보기는 허용
        self.assertEqual(code, 0)
        self.assertIn("claude mcp add", out)

    def test_unique_backup_names(self):
        t = self.tmp / "x.json"
        t.write_text("{}", encoding="utf-8")
        first = mc.unique_backup(t)
        first.write_text("", encoding="utf-8")
        self.assertNotEqual(mc.unique_backup(t), first)

    @unittest.skipUnless(os.name == "posix", "POSIX 권한·심볼릭 링크")
    def test_symlink_is_preserved_and_mode_kept(self):
        real = self.tmp / "dotfiles" / "config.toml"
        real.parent.mkdir()
        real.write_text('model = "x"\n', encoding="utf-8")
        os.chmod(real, 0o600)
        link = self.tmp / "config.toml"
        link.symlink_to(real)
        self.run_merge("codex-toml", link, "--apply")
        self.assertTrue(link.is_symlink())
        self.assertIn("basic-memory", real.read_text(encoding="utf-8"))
        self.assertEqual(real.stat().st_mode & 0o777, 0o600)

    def test_crlf_and_bom_inputs(self):
        t = self.tmp / "crlf.toml"
        t.write_bytes(b'model = "x"\r\nname = "y"\r\n')
        self.run_merge("codex-toml", t, "--apply")
        raw = t.read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))  # 모든 줄바꿈이 CRLF 유지
        self.assertEqual(tomllib.loads(raw.decode())["name"], "y")
        j = self.tmp / "bom.json"
        j.write_bytes(b"\xef\xbb\xbf" + b'{"theme": "dark"}')
        self.run_merge("claude-json", j, "--apply")
        self.assertEqual(json.loads(j.read_text(encoding="utf-8-sig"))["theme"], "dark")


def github_slug(heading: str) -> str:
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


class RepoConsistencyTests(unittest.TestCase):
    def md_files(self, include_demo=False):
        return [p for p in ROOT.rglob("*.md") if ".git" not in p.parts and (include_demo or "demo-vault" not in p.parts)]

    def test_examples_parse(self):
        json.loads((ROOT / "examples/claude-mcp.json").read_text(encoding="utf-8"))
        json.loads((ROOT / "examples/tunnel-profile.json").read_text(encoding="utf-8"))
        tomllib.loads((ROOT / "examples/codex-mcp.toml").read_text(encoding="utf-8"))
        plistlib.loads((ROOT / "examples/com.example.ai-vault-tunnel.plist").read_bytes())

    def test_example_project_ids_agree(self):
        ids = {
            json.loads((ROOT / "examples/claude-mcp.json").read_text(encoding="utf-8"))["mcpServers"]["basic-memory"]["args"][-1],
            tomllib.loads((ROOT / "examples/codex-mcp.toml").read_text(encoding="utf-8"))["mcp_servers"]["basic-memory"]["args"][-1],
            json.loads((ROOT / "examples/tunnel-profile.json").read_text(encoding="utf-8"))["mcp"]["commands"][0]["command"].split()[-1],
        }
        self.assertEqual(ids, {"ai-vault"})

    def test_relative_markdown_links_and_anchors_resolve(self):
        bad = []
        for f in self.md_files():
            text = re.sub(r"```.*?```", "", f.read_text(encoding="utf-8"), flags=re.S)
            for target in re.findall(r"\]\(([^)\s]+)\)", text):
                if re.match(r"^(https?:|mailto:)", target):
                    continue
                path, _, anchor = target.partition("#")
                dest = f if not path else (f.parent / path)
                if not dest.exists():
                    bad.append(f"{f.relative_to(ROOT)} -> {target} (파일 없음)")
                elif anchor and dest.suffix == ".md":
                    heads = {github_slug(m) for m in re.findall(r"^#{1,6}\s+(.+?)\s*$", dest.read_text(encoding="utf-8"), flags=re.M)}
                    if anchor not in heads:
                        bad.append(f"{f.relative_to(ROOT)} -> {target} (앵커 없음)")
        self.assertEqual(bad, [])

    def test_demo_vault_wikilinks_resolve(self):
        vault = ROOT / "examples" / "demo-vault"
        bad = []
        for f in vault.rglob("*.md"):
            for target in re.findall(r"\[\[([^\]|#]+)", f.read_text(encoding="utf-8")):
                if not (vault / f"{target}.md").exists():
                    bad.append(f"{f.relative_to(vault)} -> [[{target}]]")
        self.assertEqual(bad, [])

    def test_demo_vault_has_current_and_history_roles(self):
        roles = {}
        for f in (ROOT / "examples" / "demo-vault").rglob("*.md"):
            roles[f.name] = vd._front_value(f, "context_role")
        self.assertEqual(roles["Sample-Notes-App.md"], "current")
        self.assertEqual(roles["2026-01-05-검색-검증.md"], "history")

    def test_scripts_compile_and_guard_precedes_tomllib(self):
        for s in (ROOT / "scripts").glob("*.py"):
            src = s.read_text(encoding="utf-8")
            compile(src, str(s), "exec")  # 문법 검사만 (파일을 쓰지 않음)
            if "import tomllib" in src:
                self.assertLess(src.index("sys.version_info < (3, 11)"), src.index("import tomllib"), s.name)

    def test_handoff_template_and_instructions_carry_the_new_fields(self):
        handoff = (ROOT / "templates/handoff.md").read_text(encoding="utf-8")
        for key in ("## 현재 상태", "## 보류·금지 범위", "## 확인된 사실 / 추정", "빌드·테스트", "설치·실제 실행", "실사용"):
            self.assertIn(key, handoff)
        for rel in ("prompts/shared-context.md", "templates/vault-readme.md"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("보류·금지", text, rel)

    def test_license_is_mit_and_linked_from_readme(self):
        lic = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(lic.startswith("MIT License"))
        self.assertRegex(lic, r"Copyright \(c\) 20\d\d \S+")
        self.assertIn("[MIT](LICENSE)", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_display_name_is_consistent_in_docs(self):
        """문서의 호칭은 AI-Vault로 통일 (짧은 'Vault(`ai-vault`)' 표기는 바꾸기 전까지 쓰지 않음)."""
        offenders = [str(f.relative_to(ROOT)) for f in self.md_files() if re.search(r"(?<![A-Za-z-])Vault\(`ai-vault`\)", f.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [])

    def test_no_secrets_emails_or_personal_paths_in_repo(self):
        pat = re.compile("|".join(r.pattern for r in vd.SECRET_PATTERNS.values()))
        email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")
        user_path = re.compile(r"(?:/Users/|/home/|C:\\Users\\)(?!me\b|name\b|USER\b|you\b)[A-Za-z0-9._-]+")
        home = str(Path.home())
        hits = []
        for f in ROOT.rglob("*"):
            if f.is_file() and ".git" not in f.parts and f.suffix in {".md", ".json", ".toml", ".py", ".plist", ".sh", ".yml", ".yaml"}:
                t = f.read_text(encoding="utf-8", errors="ignore")
                if pat.search(t) or email.search(t) or user_path.search(t) or (len(home) > 5 and home in t):
                    hits.append(str(f.relative_to(ROOT)))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
