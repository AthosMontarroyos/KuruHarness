import tempfile
import unittest
from pathlib import Path

from harness import review_flow as rf

GOOD = "--- a/CLAUDE.md\n+++ b/CLAUDE.md\n@@ -1,0 +1,1 @@\n+- Regra nova qualquer sobre estilo.\n"
BAD = "--- /dev/null\n+++ b/.claude/agents/x.md\n@@ -0,0 +1,5 @@\n+---\n+name: x\n+description: y\n+tools: Read\n+---\n"


class FlowTest(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.state = Path(t.name) / "reviews.json"

    def check(self, diff, task="t"):
        return rf.check(task, diff, state_path=self.state)

    def test_deterministic_rejects_without_model(self):
        out = self.check(BAD)
        self.assertEqual((out["stage"], out["verdict"]), ("deterministic", "REPROVADO"))
        self.assertNotIn("agent", out)

    def test_clean_diff_goes_to_reviewer_with_only_relevant_rules(self):
        out = self.check(GOOD)
        self.assertEqual((out["verdict"], out["agent"]), ("PENDENTE", "reviewer"))
        self.assertIn("1. ", out["packet"])
        self.assertIn("5. ", out["packet"])  # CLAUDE.md -> regra 5
        self.assertNotIn("2. Todo subagent", out["packet"])  # R2 não é relevante aqui
        self.assertIn(GOOD, out["packet"])

    def test_escalates_to_opus_after_two_haiku_rejections(self):
        self.assertEqual(self.check(GOOD)["agent"], "reviewer")
        self.assertEqual(rf.record("t", "reviewer", "REPROVADO", self.state)["next"], "CORRIGIR")
        self.assertEqual(self.check(GOOD)["agent"], "reviewer")
        out = rf.record("t", "reviewer", "REPROVADO", self.state)
        self.assertEqual(out["proximo_revisor"], "reviewer-senior")
        self.assertEqual(self.check(GOOD)["agent"], "reviewer-senior")

    def test_stops_at_three_rejections(self):
        rf.record("t", "reviewer", "REPROVADO", self.state)
        rf.record("t", "reviewer", "REPROVADO", self.state)
        self.assertEqual(rf.record("t", "reviewer-senior", "REPROVADO", self.state)["next"], "PARAR")
        self.assertEqual(self.check(GOOD)["verdict"], "PARAR")

    def test_deterministic_rejections_count_toward_limit(self):
        for _ in range(3):
            out = self.check(BAD)
        self.assertEqual(out["next"], "PARAR")
        self.assertEqual(self.check(GOOD)["verdict"], "PARAR")

    def test_approval_resets_task(self):
        rf.record("t", "reviewer", "REPROVADO", self.state)
        self.assertEqual(rf.record("t", "reviewer", "APROVADO", self.state)["next"], "FIM")
        self.assertEqual(self.check(GOOD)["agent"], "reviewer")

    def test_tasks_are_independent(self):
        rf.record("a", "reviewer", "REPROVADO", self.state)
        rf.record("a", "reviewer", "REPROVADO", self.state)
        self.assertEqual(self.check(GOOD, "b")["agent"], "reviewer")

    def test_invalid_args(self):
        with self.assertRaises(ValueError):
            rf.record("t", "x", "APROVADO", self.state)
        with self.assertRaises(ValueError):
            rf.record("t", "reviewer", "talvez", self.state)


if __name__ == "__main__":
    unittest.main()
