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

    def test_small_diff_is_one_packet(self):
        out = self.check(GOOD)
        self.assertEqual(len(out["packets"]), 1)
        self.assertEqual(out["packet"], out["packets"][0])

    def test_large_diff_is_split_by_file_with_own_rules(self):
        big = "".join(
            f"--- a/{n}\n+++ b/{n}\n@@ -1,0 +1,40 @@\n" + "".join(f"+linha {i} de {n}\n" for i in range(40))
            for n in ("TASKS.md", "docs/a.md", "docs/b.md")
        )
        pk = rf.packets(big, limit=600)
        self.assertGreater(len(pk), 1)
        joined = "".join(pk)
        for n in ("TASKS.md", "docs/a.md", "docs/b.md"):
            self.assertEqual(joined.count(f"+++ b/{n}"), 1)  # nenhum arquivo cortado ou repetido
        self.assertIn("4. Nenhuma fase", pk[0])  # TASKS.md -> regra 4
        self.assertNotIn("4. Nenhuma fase", pk[-1])  # o pacote sem TASKS.md não carrega a regra 4
        old, rf.MAX_PACKET_CHARS = rf.MAX_PACKET_CHARS, 600
        self.addCleanup(setattr, rf, "MAX_PACKET_CHARS", old)
        out = rf.check("g", big, state_path=self.state)
        self.assertIsNone(out["packet"])
        self.assertGreater(len(out["packets"]), 1)

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
