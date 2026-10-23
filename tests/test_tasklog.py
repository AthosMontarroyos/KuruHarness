import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from harness import tasklog


class TaskLogTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "sub" / "tasks.jsonl"

    def add(self, **kw):
        base = dict(task_id="t", model="sonnet", tokens_in=10, tokens_out=5,
                    result="ok", attempts=1, path=self.path)
        base.update(kw)
        return tasklog.append_record(**base)

    def test_append_writes_one_json_line(self):
        rec = self.add()
        lines = self.path.read_text().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0]), rec)

    def test_rejects_invalid(self):
        for kw in ({"attempts": 4}, {"attempts": 0}, {"result": "x"},
                   {"tokens_in": -1}, {"model": ""}, {"attempts": True}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.add(**kw)
        self.assertFalse(self.path.exists())

    def test_summarize_by_model(self):
        self.add(model="haiku", result="ok", attempts=1)
        self.add(model="haiku", result="fail", attempts=3, tokens_in=20)
        self.add(model="opus", result="ok", attempts=2)
        s = tasklog.summarize(self.path)
        self.assertEqual(s["haiku"], {"count": 2, "tokens_in": 30, "tokens_out": 10,
                                      "success_rate": 0.5, "avg_attempts": 2.0})
        self.assertEqual(s["opus"]["avg_attempts"], 2.0)

    def test_missing_file_is_empty(self):
        self.assertEqual(tasklog.summarize(self.path), {})

    def test_corrupt_lines_are_skipped_and_counted(self):
        self.add()
        with self.path.open("a") as f:
            f.write("not json\n\n")
        s = tasklog.summarize(self.path)
        self.assertEqual(s["_skipped"], 1)
        self.assertEqual(s["sonnet"]["count"], 1)

    def test_cli(self):
        base = ["--path", str(self.path)]
        add = ["add", "--task-id", "t1", "--model", "sonnet", "--tokens-in", "100",
               "--tokens-out", "50", "--result", "ok"] + base
        self.assertEqual(tasklog.main(add + ["--attempts", "1"]), 0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(tasklog.main(add + ["--attempts", "4"]), 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tasklog.main(["summary", "--json"] + base), 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["sonnet"]["count"], 1)
        self.assertEqual(data["sonnet"]["success_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
