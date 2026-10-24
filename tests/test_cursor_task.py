import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "cursor-task.sh"

FAKE_AGENT = """#!/usr/bin/env bash
echo "$@" > "$FAKE_ARGS"
pwd > "$FAKE_CWD"
echo "feito pelo agent falso" > saida.txt
exit "${FAKE_EXIT:-0}"
"""


class CursorTaskTest(unittest.TestCase):
    """Roda o script de verdade com um `agent` falso (o Cursor CLI não existe no CI)."""

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.d = Path(t.name)
        self.repo = self.d / "repo"
        self.repo.mkdir()
        run = lambda *a: subprocess.run(a, cwd=self.repo, check=True, capture_output=True)
        run("git", "init", "-q")
        (self.repo / "README.md").write_text("oi\n")
        run("git", "add", "-A")
        run("git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "i")
        self.bin = self.d / "bin"
        self.bin.mkdir()
        (self.bin / "agent").write_text(FAKE_AGENT)
        (self.bin / "agent").chmod(0o755)
        (self.repo / "prompt.txt").write_text("faça X")
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}", CLAUDE_PROJECT_DIR=str(self.repo),
                        FAKE_ARGS=str(self.d / "args"), FAKE_CWD=str(self.d / "cwd"))

    def run_script(self, *args, env=None):
        return subprocess.run(["bash", str(SCRIPT), *args], cwd=self.repo, env=env or self.env,
                              capture_output=True, text=True)

    def test_runs_in_worktree_and_returns_diff(self):
        r = self.run_script("t1", "prompt.txt")
        self.assertEqual(r.returncode, 0, r.stderr)
        diff = (self.repo / ".claude/state/cursor/t1.diff").read_text()
        self.assertIn("saida.txt", diff)
        self.assertIn("agent falso", diff)
        self.assertFalse((self.repo / "saida.txt").exists())  # o repo principal não foi tocado
        cwd = (self.d / "cwd").read_text().strip()
        self.assertTrue(cwd.endswith(".claude/worktrees/t1"), cwd)

    def test_agent_flags_model_fixed_and_fresh_session(self):
        self.run_script("t2", "prompt.txt")
        args = (self.d / "args").read_text()
        for flag in ("-p", "--trust", "--mode agent", "--model grok-4.7-high-fast"):
            self.assertIn(flag, args)
        self.assertNotIn("--resume", args)
        self.assertNotIn("--continue", args)
        self.assertIn("faça X", args)

    def test_model_can_be_overridden(self):
        self.run_script("t3", "prompt.txt", env=dict(self.env, CURSOR_MODEL="outro-modelo"))
        self.assertIn("--model outro-modelo", (self.d / "args").read_text())

    def test_max_three_in_parallel(self):
        slots = self.repo / ".claude/state/cursor/slots"
        sleepers = [subprocess.Popen(["sleep", "30"]) for _ in range(3)]
        self.addCleanup(lambda: [(p.kill(), p.wait()) for p in sleepers])
        for i, p in enumerate(sleepers, 1):
            (slots / str(i)).mkdir(parents=True)
            (slots / str(i) / "pid").write_text(str(p.pid))
        r = self.run_script("t4", "prompt.txt")
        self.assertEqual(r.returncode, 75)
        self.assertIn("sem vaga", r.stderr)
        self.assertFalse((self.repo / ".claude/worktrees/t4").exists())

    def test_dead_slot_is_reused_and_released(self):
        slots = self.repo / ".claude/state/cursor/slots"
        for i in (1, 2, 3):
            (slots / str(i)).mkdir(parents=True)
            (slots / str(i) / "pid").write_text("999999")  # processo que não existe
        self.assertEqual(self.run_script("t5", "prompt.txt").returncode, 0)
        self.assertFalse((slots / "1").exists())  # a vaga reaproveitada foi liberada ao fim
        self.assertTrue((slots / "2").exists() and (slots / "3").exists())  # as outras ficam como estavam

    def test_agent_failure_propagates_but_diff_is_kept(self):
        r = self.run_script("t6", "prompt.txt", env=dict(self.env, FAKE_EXIT="3"))
        self.assertEqual(r.returncode, 3)
        self.assertTrue((self.repo / ".claude/state/cursor/t6.diff").exists())

    def test_clean_removes_worktree_and_branch(self):
        self.run_script("t7", "prompt.txt")
        self.assertEqual(self.run_script("--clean", "t7").returncode, 0)
        self.assertFalse((self.repo / ".claude/worktrees/t7").exists())
        branches = subprocess.run(["git", "branch"], cwd=self.repo, capture_output=True, text=True).stdout
        self.assertNotIn("cursor/t7", branches)

    def test_invalid_id_and_missing_agent(self):
        self.assertEqual(self.run_script("../x", "prompt.txt").returncode, 2)
        env = dict(self.env, PATH="/usr/bin:/bin")
        self.assertEqual(self.run_script("t8", "prompt.txt", env=env).returncode, 127)


if __name__ == "__main__":
    unittest.main()
