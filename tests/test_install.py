import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- kuru-harness:start -->", "<!-- kuru-harness:end -->"


class InstallTest(unittest.TestCase):
    """Roda install.sh de verdade contra o checkout local (KURU_SRC_DIR), num projeto com config própria."""

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.p = Path(t.name)
        (self.p / ".claude").mkdir()
        (self.p / ".claude/settings.json").write_text(json.dumps({
            "model": "opus",
            "permissions": {"allow": ["Bash(npm test)"]},
            "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo meu-hook"}]}]},
        }))
        (self.p / "CLAUDE.md").write_text("# Meu projeto\nregra minha\n")
        (self.p / "SPEC.md").write_text("# Minha spec\nalgo meu\n")
        (self.p / ".gitignore").write_text("node_modules/\n")

    def install(self):
        env = dict(os.environ, KURU_SRC_DIR=str(ROOT))
        return subprocess.run(["bash", str(ROOT / "install.sh")], cwd=self.p, env=env, capture_output=True, text=True)

    def test_installs_kit_and_keeps_project_files(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        for f in ("harness/route.py", "harness/review_flow.py", "scripts/end-of-task.sh", "scripts/cursor-task.sh",
                  ".claude/agents/reviewer.md", ".claude/agents/implementer-sonnet.md", ".claude/commands/task.md"):
            self.assertTrue((self.p / f).exists(), f)
        self.assertFalse((self.p / "harness/eval").exists())
        self.assertFalse((self.p / "tests").exists())
        s = json.loads((self.p / ".claude/settings.json").read_text())
        self.assertEqual(s["model"], "opus")  # config do projeto preservada
        self.assertIn("Bash(npm test)", s["permissions"]["allow"])
        self.assertIn("Bash(python3 -m harness.route *)", s["permissions"]["allow"])
        cmds = [h["command"] for g in s["hooks"]["Stop"] for h in g["hooks"]]
        self.assertIn("echo meu-hook", cmds)
        self.assertTrue(any("end-of-task.sh" in c for c in cmds))
        claude = (self.p / "CLAUDE.md").read_text()
        self.assertTrue(claude.startswith("# Meu projeto\nregra minha"))
        self.assertIn("## Regras gerais", claude)
        self.assertNotIn("## Escopo", claude)
        self.assertIn("algo meu", (self.p / "SPEC.md").read_text())
        self.assertIn("node_modules/", (self.p / ".gitignore").read_text())
        self.assertIn(".claude/state/", (self.p / ".gitignore").read_text())

    def test_is_idempotent(self):
        self.install()
        first = {f: (self.p / f).read_text() for f in (".claude/settings.json", "CLAUDE.md", "SPEC.md", ".gitignore")}
        self.assertEqual(self.install().returncode, 0)
        for f, before in first.items():
            self.assertEqual((self.p / f).read_text(), before, f)
        self.assertEqual((self.p / "CLAUDE.md").read_text().count(START), 1)

    def test_installed_kit_actually_works(self):
        self.install()
        r = subprocess.run(["python3", "-m", "harness.route", "corrigir typo", "--files", "a.md"],
                           cwd=self.p, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["tier"], "trivial")
        diff = "--- a/CLAUDE.md\n+++ b/CLAUDE.md\n@@ -1,0 +1,1 @@\n+- nota\n"
        r = subprocess.run(["python3", "-m", "harness.review_flow", "check", "--task", "x"], input=diff,
                           cwd=self.p, capture_output=True, text=True)
        out = json.loads(r.stdout)
        self.assertEqual(out["verdict"], "PENDENTE")
        self.assertIn("1. Nenhum segredo", out["packet"])  # as regras vieram do SPEC.md mesclado

    def test_refuses_foreign_harness_dir_and_changes_nothing(self):
        (self.p / "harness").mkdir()
        (self.p / "harness/outra_coisa.py").write_text("x = 1\n")
        r = self.install()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("não é do kit", r.stderr)
        self.assertFalse((self.p / "scripts").exists())
        self.assertEqual((self.p / "CLAUDE.md").read_text(), "# Meu projeto\nregra minha\n")

    def test_missing_kit_fails_cleanly(self):
        empty = self.p / "vazio"
        empty.mkdir()
        env = dict(os.environ, KURU_SRC_DIR=str(empty))
        r = subprocess.run(["bash", str(ROOT / "install.sh")], cwd=self.p, env=env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("kit não encontrado", r.stderr)


if __name__ == "__main__":
    unittest.main()
