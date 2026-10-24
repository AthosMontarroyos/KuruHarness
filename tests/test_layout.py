import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class LayoutTest(unittest.TestCase):
    def test_every_agent_declares_model(self):
        agents = sorted((ROOT / ".claude/agents").glob("*.md"))
        self.assertGreaterEqual(len(agents), 6)
        for a in agents:
            self.assertRegex(a.read_text(encoding="utf-8"), r"(?m)^model:\s*\S+", a.name)

    def test_plugin_packaging_is_gone(self):
        # o plugin foi removido de propósito (prefixos obrigatórios e o CLAUDE.md não carrega); não pode voltar sem decisão
        for p in (".claude-plugin", "hooks", "agents", "commands", "install.sh"):
            self.assertFalse((ROOT / p).exists(), p)

    def test_stop_hook_is_in_project_settings(self):
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        cmd = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertIn("end-of-task.sh", cmd)
        self.assertTrue((ROOT / "scripts/end-of-task.sh").exists())

    def test_commands_call_the_repo_launcher(self):
        for f in list((ROOT / ".claude/commands").glob("*.md")) + list((ROOT / ".claude/agents").glob("*.md")):
            text = f.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"python3 -m harness", f.name)
            self.assertNotIn("kuru-harness", text, f.name)
            self.assertNotRegex(text, r"(?<!bin/)kuru (route|check-rules|review-flow|tasklog|cursor-task)\b", f.name)

    def test_windows_safe_line_endings_configured(self):
        ga = (ROOT / ".gitattributes").read_text()
        self.assertIn("*.sh text eol=lf", ga)
        self.assertIn("bin/* text eol=lf", ga)
        for f in (ROOT / "bin/kuru", ROOT / "scripts/end-of-task.sh", ROOT / "scripts/cursor-task.sh"):
            self.assertNotIn(b"\r", f.read_bytes(), f.name)  # CRLF quebraria o shebang

    def test_launcher_is_executable_in_git(self):
        out = subprocess.run(["git", "ls-files", "-s", "bin/kuru"], cwd=ROOT, capture_output=True, text=True).stdout
        self.assertTrue(out.startswith("100755"), out)


class LauncherTest(unittest.TestCase):
    """bin/kuru escolhe um Python 3 que RODA, ignorando o atalho quebrado da Microsoft Store."""

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.bin = Path(t.name)

    def fake(self, name, body):
        p = self.bin / name
        p.write_text("#!/bin/sh\n" + body + "\n")
        p.chmod(p.stat().st_mode | stat.S_IEXEC)

    def run_kuru(self, path):
        env = dict(os.environ, PATH=path)
        return subprocess.run(["bash", str(ROOT / "bin/kuru"), "route", "corrigir typo", "--files", "a.md"],
                              env=env, capture_output=True, text=True)

    def test_skips_broken_python3_stub_and_uses_python(self):
        real = subprocess.run(["bash", "-c", "command -v python3"], capture_output=True, text=True).stdout.strip()
        self.fake("python3", 'echo "Python was not found; run without arguments to install from the Microsoft Store" >&2; exit 9')
        os.symlink(real, self.bin / "python")
        r = self.run_kuru(f"{self.bin}:/usr/bin:/bin")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["tier"], "trivial")

    def test_skips_python2_style_interpreter(self):
        self.fake("python3", 'exit 1')  # roda mas não é Python 3
        r = self.run_kuru(f"{self.bin}:/usr/bin:/bin")
        self.assertEqual(r.returncode, 0, r.stderr)  # cai no python3 real do sistema

    def test_clear_error_when_no_python(self):
        empty = tempfile.mkdtemp()
        r = subprocess.run([ "/bin/bash", str(ROOT / "bin/kuru"), "route", "x"], env={"PATH": empty},
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 127)
        self.assertIn("Python 3 não encontrado", r.stderr)

    def test_unknown_command_and_help(self):
        env = dict(os.environ)
        r = subprocess.run(["bash", str(ROOT / "bin/kuru"), "nada"], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        r = subprocess.run(["bash", str(ROOT / "bin/kuru"), "--help"], env=env, capture_output=True, text=True)
        self.assertIn("route", r.stdout)


if __name__ == "__main__":
    unittest.main()
