import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness import brief, worktree

ROOT = Path(__file__).resolve().parent.parent
GIT = ["git", "-c", "user.email=a@b", "-c", "user.name=t"]


def sh(cmd, cwd):
    return subprocess.run(cmd, shell=True, cwd=cwd, check=True, capture_output=True, text=True).stdout


class WorktreeTest(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.d = Path(t.name).resolve()
        (self.d / ".gitignore").write_text(".kuru/\n.claude/state/\n")
        (self.d / "a.txt").write_text("um\n")
        sh("git init -q && git add -A && git -c user.email=a@b -c user.name=t commit -qm i", self.d)
        old = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, old)

    def commit_in(self, wt, name="novo.txt"):
        (Path(wt) / name).write_text("x\n")
        subprocess.run([*GIT, "-C", wt, "add", name], check=True)
        subprocess.run([*GIT, "-C", wt, "commit", "-qm", "c"], check=True)

    def test_create_makes_isolated_branch_and_marks_it_active(self):
        res = worktree.create("t1")
        self.assertEqual(res["branch"], "kuru/t1")
        self.assertTrue((Path(res["path"]) / "a.txt").exists())
        self.assertEqual((self.d / ".kuru/active-worktree").read_text().splitlines(), [res["path"], res["base"]])
        self.assertEqual(sh("git branch --show-current", res["path"]).strip(), "kuru/t1")

    def test_worktree_starts_from_last_commit_not_from_users_uncommitted_edits(self):
        (self.d / "a.txt").write_text("edição do usuário na IDE\n")
        res = worktree.create("t1")
        self.assertEqual((Path(res["path"]) / "a.txt").read_text(), "um\n")
        self.assertEqual((self.d / "a.txt").read_text(), "edição do usuário na IDE\n")  # intocado

    def test_edits_in_worktree_do_not_touch_main_tree(self):
        res = worktree.create("t1")
        (Path(res["path"]) / "a.txt").write_text("do claude\n")
        self.commit_in(res["path"])
        self.assertEqual((self.d / "a.txt").read_text(), "um\n")
        self.assertFalse((self.d / "novo.txt").exists())
        self.assertEqual(sh("git status --porcelain", self.d).strip(), "")

    def test_only_one_active_worktree_and_bad_ids_are_refused(self):
        worktree.create("t1")
        with self.assertRaises(worktree.WorktreeError):
            worktree.create("t2")
        for bad in ("", "../x", "a b", "-x"):
            with self.assertRaises(worktree.WorktreeError, msg=bad):
                worktree.check_id(bad)

    def test_status_reports_commits_ahead_and_merge_command(self):
        res = worktree.create("t1")
        self.commit_in(res["path"])
        (e,) = worktree.entries(self.d)
        self.assertEqual((e["id"], e["commits_a_frente"], e["sujo"], e["mesclar"]), ("t1", 1, False, "git merge kuru/t1"))

    def test_remove_refuses_unmerged_work_then_succeeds_after_merge(self):
        res = worktree.create("t1")
        self.commit_in(res["path"])
        with self.assertRaises(worktree.WorktreeError):
            worktree.remove("t1")
        self.assertTrue(Path(res["path"]).exists())
        sh("git -c user.email=a@b -c user.name=t merge -q kuru/t1", self.d)
        worktree.remove("t1")
        self.assertFalse(Path(res["path"]).exists())
        self.assertFalse((self.d / ".kuru/active-worktree").exists())
        self.assertNotIn("kuru/t1", sh("git branch", self.d))
        self.assertTrue((self.d / "novo.txt").exists())  # o trabalho mesclado ficou

    def test_remove_refuses_dirty_worktree_but_force_discards(self):
        res = worktree.create("t1")
        (Path(res["path"]) / "a.txt").write_text("sem commit\n")
        with self.assertRaises(worktree.WorktreeError):
            worktree.remove("t1")
        worktree.remove("t1", force=True)
        self.assertFalse(Path(res["path"]).exists())

    def test_cli_is_wired(self):
        r = subprocess.run(["bash", str(ROOT / "bin/kuru"), "worktree", "create", "t1"], cwd=self.d, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["branch"], "kuru/t1")
        r = subprocess.run(["bash", str(ROOT / "bin/kuru"), "worktree", "create", "t2"], cwd=self.d, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)


class BriefWorkdirTest(unittest.TestCase):
    def test_workdir_section_only_when_given(self):
        self.assertNotIn("Onde trabalhar", brief.build("x", rules="- r"))
        text = brief.build("x", rules="- r", workdir=".kuru/worktrees/t1")
        self.assertIn("# Onde trabalhar", text)
        self.assertIn(".kuru/worktrees/t1", text)
        self.assertIn("NÃO toque no diretório principal", text)
        self.assertLess(text.index("# Onde trabalhar"), text.index("# Arquivos"))


class HookInWorktreeTest(unittest.TestCase):
    """O hook confere o worktree ativo: edição quebrada do usuário na árvore principal não reprova o Claude."""

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.d = Path(t.name).resolve()
        for sub in ("harness", "scripts", "bin", "tests"):
            (self.d / sub).mkdir()
        for f in (".gitignore", "bin/kuru", "scripts/end-of-task.sh", *[f"harness/{n}.py" for n in
                  ("__init__", "cli", "tasklog", "hooklog", "check_rules", "worktree")]):
            (self.d / f).write_text((ROOT / f).read_text())
        (self.d / "bin/kuru").chmod(0o755)
        (self.d / "tests/__init__.py").write_text("")
        self.test_file = self.d / "tests/test_x.py"
        self.set_test(self.test_file, True)
        sh("git init -q && git add -A && git -c user.email=a@b -c user.name=t commit -qm i", self.d)
        old = os.getcwd()
        os.chdir(self.d)
        self.addCleanup(os.chdir, old)

    @staticmethod
    def set_test(path, passing):
        path.write_text("import unittest\nclass T(unittest.TestCase):\n    def test(self):\n        self.assertTrue(%s)\n" % passing)

    def run_hook(self):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.d))
        return subprocess.run(["bash", str(self.d / "scripts/end-of-task.sh")], input="", env=env, cwd=self.d,
                              capture_output=True, text=True).returncode

    def log(self):
        p = self.d / ".claude/state/tasks.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def test_users_broken_edit_in_main_tree_does_not_block_claude(self):
        res = worktree.create("t1")
        self.set_test(self.test_file, False)  # o usuário quebrou um teste na IDE
        self.assertEqual(self.run_hook(), 0)

    def test_failure_inside_worktree_blocks(self):
        res = worktree.create("t1")
        self.set_test(Path(res["path"]) / "tests/test_x.py", False)
        self.assertEqual(self.run_hook(), 2)

    def test_committed_work_in_worktree_is_logged_in_main_state(self):
        res = worktree.create("t1")
        (Path(res["path"]) / "novo.txt").write_text("x\n")
        sh("git add -A && git -c user.email=a@b -c user.name=t commit -qm c", res["path"])  # árvore do worktree limpa
        self.assertEqual(self.run_hook(), 0)
        (rec,) = self.log()
        self.assertEqual((rec["result"], rec["attempts"]), ("ok", 1))
        self.assertFalse((Path(res["path"]) / ".claude/state").exists())

    def test_without_active_worktree_behaves_as_before(self):
        self.set_test(self.test_file, False)
        self.assertEqual(self.run_hook(), 2)


if __name__ == "__main__":
    unittest.main()
