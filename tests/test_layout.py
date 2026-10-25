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

    def test_auditor_is_read_only_and_has_1m_context(self):
        # o auditor lê muito: precisa de modelo com 1M nativo (Haiku 5.5, Sonnet 5+) e não pode editar nada
        text = (ROOT / ".claude/agents/auditor.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^model:\s*claude-haiku-5-5\s*$")
        tools = re.search(r"(?m)^tools:\s*(.*)$", text).group(1)
        for forbidden in ("Edit", "Write", "Bash", "NotebookEdit"):
            self.assertNotIn(forbidden, tools)

    def test_plugin_packaging_is_gone(self):
        # o plugin foi removido de propósito (prefixos obrigatórios e o CLAUDE.md não carrega); não pode voltar sem decisão
        for p in (".claude-plugin", "hooks", "agents", "commands", "install.sh"):
            self.assertFalse((ROOT / p).exists(), p)

    def test_stop_hook_is_in_project_settings(self):
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        cmd = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertIn("end-of-task.sh", cmd)
        self.assertTrue((ROOT / "scripts/end-of-task.sh").exists())

    def test_agents_and_skills_call_the_repo_launcher(self):
        for f in list((ROOT / ".claude/skills").glob("*/SKILL.md")) + list((ROOT / ".claude/agents").glob("*.md")):
            text = f.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"python3 -m harness", f.name)
            self.assertNotIn("kuru-harness", text, f.name)
            self.assertNotRegex(text, r"(?<!bin/)kuru (route|check-rules|review-flow|tasklog)\b", f.name)

    # ---- autonomia e economia de tokens ----
    def test_every_agent_runs_isolated_without_claude_md(self):
        for a in (ROOT / ".claude/agents").glob("*.md"):
            text = a.read_text(encoding="utf-8")
            self.assertRegex(text, r"(?m)^omitClaudeMd:\s*true\s*$", a.name)
            self.assertIn("SEM contexto", text, a.name)  # cada agente sabe que não vê a conversa

    def test_every_agent_description_says_when_not_to_use_it_or_that_it_is_a_fallback(self):
        for a in (ROOT / ".claude/agents").glob("*.md"):
            desc = re.search(r"(?m)^description:\s*(.+)$", a.read_text(encoding="utf-8")).group(1)
            self.assertRegex(desc, r"(?i)\b(n[aã]o use|n[aã]o serve|reserva|n[aã]o é)\b", a.name)

    def test_claude_md_stays_small_because_it_is_loaded_every_turn(self):
        size = len((ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertLessEqual(size, 6000, f"CLAUDE.md com {size} caracteres: detalhe vai para skill/agent, não para cá")

    def test_delegation_procedure_is_a_skill_the_model_can_pick_itself(self):
        skill = (ROOT / ".claude/skills/delegar/SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(skill, r"(?m)^name:\s*delegar\s*$")
        self.assertRegex(skill, r"(?m)^description:\s*.*[Nn]ão use para tarefa trivial")
        self.assertNotIn("disable-model-invocation", skill)  # o Claude precisa poder acionar sozinho
        self.assertIn("skill `delegar`", (ROOT / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_nothing_mentions_slash_commands_that_no_longer_exist(self):
        for f in (ROOT / "CLAUDE.md", ROOT / "README.md", *(ROOT / ".claude/skills").glob("*/SKILL.md"), *(ROOT / ".claude/agents").glob("*.md")):
            self.assertNotRegex(f.read_text(encoding="utf-8"), r"(?<![\w/])/(task|review|fallback)\b", f.name)

    def test_windows_safe_line_endings_configured(self):
        ga = (ROOT / ".gitattributes").read_text()
        self.assertIn("*.sh text eol=lf", ga)
        self.assertIn("bin/* text eol=lf", ga)
        for f in (ROOT / "bin/kuru", ROOT / "scripts/end-of-task.sh"):
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
