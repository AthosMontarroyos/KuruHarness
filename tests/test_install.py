import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness import install

ROOT = Path(__file__).resolve().parent.parent


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name) / ".claude"
        self.dest.mkdir()
        (self.dest / "settings.json").write_text(json.dumps({"model": "opus", "permissions": {"allow": ["Bash(ls*)"]}}), encoding="utf-8")
        (self.dest / "CLAUDE.md").write_text("# Meu global\nregra minha\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_installs_everything_and_keeps_user_config(self):
        rep = install.install(self.dest)
        self.assertEqual(rep["conflitos"], [])
        for rel in ("agents/planner.md", "agents/auditor.md", "skills/delegar/SKILL.md", "kuru/bin/kuru", "kuru/harness/route.py", "kuru/CLAUDE.md"):
            self.assertTrue((self.dest / rel).exists(), rel)
        settings = json.loads((self.dest / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["model"], "opus")
        self.assertIn("Bash(ls*)", settings["permissions"]["allow"])
        hook = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertIn("end-of-task.sh --diff", hook)
        self.assertEqual(settings["hooks"]["Stop"][0]["hooks"][0]["shell"], "bash")
        md = (self.dest / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("regra minha", md)
        self.assertIn(install.BEGIN, md)
        self.assertTrue((self.dest / "CLAUDE.md.kuru-bak").exists())

    def test_commands_are_rewritten_to_the_global_path(self):
        install.install(self.dest)
        base = (self.dest / "kuru").resolve().as_posix()
        for f in list((self.dest / "agents").glob("*.md")) + list((self.dest / "skills").glob("*/SKILL.md")):
            text = f.read_text(encoding="utf-8")
            self.assertNotIn("bash bin/kuru", text, f.name)
        self.assertIn(base, (self.dest / "agents/implementer-sonnet.md").read_text(encoding="utf-8"))

    def test_global_claude_md_block_stays_small(self):
        rep = install.install(self.dest)
        self.assertLess(rep["claude_md_chars_por_turno"], 4500)

    def test_idempotent_and_no_duplicates(self):
        install.install(self.dest)
        again = install.install(self.dest)
        self.assertEqual(again["copiados"], 0)
        md = (self.dest / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertEqual(md.count(install.BEGIN), 1)
        settings = json.loads((self.dest / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(len(settings["hooks"]["Stop"]), 1)
        self.assertEqual(len(settings["permissions"]["allow"]), len(set(settings["permissions"]["allow"])))

    def test_user_file_with_same_name_is_not_overwritten_without_force(self):
        (self.dest / "agents").mkdir()
        mine = self.dest / "agents" / "planner.md"
        mine.write_text("meu planner\n", encoding="utf-8")
        rep = install.install(self.dest)
        self.assertIn("agents/planner.md", rep["conflitos"])
        self.assertEqual(mine.read_text(encoding="utf-8"), "meu planner\n")
        install.install(self.dest, force=True)
        self.assertNotEqual(mine.read_text(encoding="utf-8"), "meu planner\n")

    def test_files_the_kit_no_longer_ships_are_removed_unless_edited(self):
        install.install(self.dest)
        gone, edited = self.dest / "kuru/scripts/velho.sh", self.dest / "agents/velho.md"
        gone.write_text("x", encoding="utf-8")
        edited.write_text("y", encoding="utf-8")
        manifest = json.loads((self.dest / "kuru/.manifest.json").read_text(encoding="utf-8"))
        manifest["kuru/scripts/velho.sh"] = install.sha("x")
        manifest["agents/velho.md"] = install.sha("original")
        (self.dest / "kuru/.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        rep = install.install(self.dest)
        self.assertEqual(rep["removidos"], ["kuru/scripts/velho.sh"])
        self.assertFalse(gone.exists())
        self.assertTrue(edited.exists())

    def test_global_block_treats_cursor_as_the_users_ide_not_as_a_cli_to_call(self):
        install.install(self.dest)
        md = (self.dest / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertNotIn("cursor-task", md)  # o Cursor não é chamado pelo Bash (integração removida)
        self.assertIn("kuru/bin/kuru worktree create", md)  # mas a convivência com a IDE vale em todo projeto
        self.assertFalse((self.dest / "kuru/scripts/cursor-task.sh").exists())
        self.assertTrue((self.dest / "kuru/harness/worktree.py").exists())

    def test_dry_run_writes_nothing(self):
        install.install(self.dest, dry_run=True)
        self.assertFalse((self.dest / "agents").exists())
        self.assertFalse((self.dest / "kuru").exists())

    def test_installed_kit_works_from_a_foreign_project(self):
        install.install(self.dest)
        proj = Path(self.tmp.name) / "proj"
        proj.mkdir()
        kuru = self.dest / "kuru/bin/kuru"
        out = subprocess.run(["bash", str(kuru), "route", "mexer em 12 arquivos"], cwd=proj, capture_output=True, text=True)
        self.assertEqual(json.loads(out.stdout)["tier"], "longa", out.stderr)
        out = subprocess.run(["bash", str(kuru), "brief", "--task", "x", "--out", ".kuru/x.prompt"], cwd=proj, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Regras do projeto", (proj / ".kuru/x.prompt").read_text(encoding="utf-8"))

    def test_manifest_records_the_clone_and_update_skill_is_installed(self):
        install.install(self.dest)
        manifest = json.loads((self.dest / "kuru/.manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["_origem"], ROOT.as_posix())
        skill = (self.dest / "skills/atualizar-kuru/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("_origem", skill)
        self.assertIn("pull --ff-only", skill)
        self.assertNotIn("--force`, ", skill.split("Com `conflitos`")[0])

    def test_reviewers_reject_input_without_a_diff(self):
        for name in ("reviewer", "reviewer-senior"):
            text = (ROOT / ".claude/agents" / f"{name}.md").read_text(encoding="utf-8")
            self.assertRegex(text, r"contexto insuficiente", name)
            self.assertIn("diff unificado", text, name)


if __name__ == "__main__":
    unittest.main()
