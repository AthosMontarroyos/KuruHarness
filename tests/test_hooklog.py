import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness import hooklog

ROOT = Path(__file__).resolve().parent.parent


def transcript(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for model, tin, tout in rows:
            f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "model": model,
                    "usage": {"input_tokens": tin, "cache_creation_input_tokens": 5,
                              "cache_read_input_tokens": 10, "output_tokens": tout}}}) + "\n")
        f.write("não é json\n")
        f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "oi"}}) + "\n")


class HookLogTest(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.dir = Path(t.name)

    def test_read_usage_sums_and_picks_main_model(self):
        tp = self.dir / "t.jsonl"
        transcript(tp, [("claude-opus", 100, 10), ("claude-haiku", 50, 5), ("claude-opus", 20, 2)])
        self.assertEqual(hooklog.read_usage(tp), ("claude-opus", 100 + 50 + 20 + 15, 17, 30))

    def test_read_usage_missing_file(self):
        self.assertEqual(hooklog.read_usage(self.dir / "nao-existe"), ("unknown", 0, 0, 0))

    def test_log_stop_records_delta_per_session(self):
        tp = self.dir / "t.jsonl"
        transcript(tp, [("claude-opus", 100, 10)])
        kw = dict(log_path=self.dir / "tasks.jsonl", mark_path=self.dir / "mark.json")
        inp = json.dumps({"session_id": "abcdef123", "transcript_path": str(tp)})
        r1 = hooklog.log_stop("ok", 1, inp, **kw)
        self.assertEqual((r1["tokens_in"], r1["tokens_out"], r1["tokens_cache"], r1["model"]), (105, 10, 10, "claude-opus"))
        transcript(tp, [("claude-opus", 100, 10), ("claude-opus", 40, 4)])
        r2 = hooklog.log_stop("fail", 3, inp, **kw)
        self.assertEqual((r2["tokens_in"], r2["tokens_out"], r2["tokens_cache"]), (45, 4, 10))
        self.assertEqual(len((self.dir / "tasks.jsonl").read_text().splitlines()), 2)

    def test_log_stop_without_input_still_logs(self):
        r = hooklog.log_stop("ok", 1, "", log_path=self.dir / "t.jsonl", mark_path=self.dir / "m.json")
        self.assertEqual((r["model"], r["tokens_in"]), ("unknown", 0))

    def test_invalid_attempts_do_not_crash_cli(self):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.dir), HOOK_INPUT="")
        r = subprocess.run(["python3", "-m", "harness.hooklog", "--result", "ok", "--attempts", "9"],
                           cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


class HookScriptTest(unittest.TestCase):
    """Roda o end-of-task.sh de verdade num repo temporário."""

    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.d = Path(t.name)
        for sub in ("harness", "scripts", "bin", "tests"):
            (self.d / sub).mkdir()
        for f in (".gitignore", "bin/kuru", "scripts/end-of-task.sh", *[f"harness/{n}.py" for n in
                  ("__init__", "cli", "tasklog", "hooklog", "check_rules")]):
            (self.d / f).write_text((ROOT / f).read_text())
        (self.d / "bin/kuru").chmod(0o755)
        (self.d / "tests/__init__.py").write_text("")
        self.test_file = self.d / "tests/test_x.py"
        self.set_test(True)
        subprocess.run("git init -q && git add -A && git -c user.email=a@b -c user.name=t commit -qm i",
                       shell=True, cwd=self.d, check=True)
        self.log = self.d / ".claude/state/tasks.jsonl"

    def set_test(self, passing):
        self.test_file.write_text("import unittest\nclass T(unittest.TestCase):\n    def test(self):\n        self.assertTrue(%s)\n" % passing)

    def run_hook(self, stdin=""):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.d))
        r = subprocess.run(["bash", str(self.d / "scripts/end-of-task.sh")], input=stdin, env=env,
                           cwd=self.d, capture_output=True, text=True)
        return r.returncode

    def records(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_clean_tree_logs_nothing(self):
        self.assertEqual(self.run_hook(), 0)
        self.assertEqual(self.records(), [])

    def test_success_with_changes_logs_ok_attempt_1(self):
        self.set_test(True); (self.d / "novo.txt").write_text("x")
        self.assertEqual(self.run_hook(json.dumps({"session_id": "s1"})), 0)
        rec = self.records()
        self.assertEqual((len(rec), rec[0]["result"], rec[0]["attempts"]), (1, "ok", 1))

    def test_recovery_after_two_failures_logs_ok_attempt_3(self):
        self.set_test(False)
        self.assertEqual(self.run_hook(), 2)
        self.assertEqual(self.run_hook(), 2)
        self.assertEqual(self.records(), [])  # falhas intermediárias não registram
        self.set_test(True)
        self.assertEqual(self.run_hook(), 0)
        rec = self.records()
        self.assertEqual((rec[0]["result"], rec[0]["attempts"]), ("ok", 3))

    def test_third_failure_logs_fail_attempt_3(self):
        self.set_test(False)
        self.assertEqual([self.run_hook() for _ in range(3)], [2, 2, 0])
        rec = self.records()
        self.assertEqual((rec[0]["result"], rec[0]["attempts"]), ("fail", 3))


if __name__ == "__main__":
    unittest.main()
