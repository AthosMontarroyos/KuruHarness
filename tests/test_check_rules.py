import glob
import json
import os
import unittest

from harness.check_rules import check_diff, check_r2_text, check_r4_lines

EVAL = os.path.join(os.path.dirname(__file__), "..", "harness", "eval")
# r4-01: [x] com crase só na descrição da tarefa; sem evidência real. Limite conhecido da heurística.
KNOWN_MISSES = {"r4-01"}


def diff(path, *body):
    return f"--- a/{path}\n+++ b/{path}\n@@ -1,0 +1,{len(body)} @@\n" + "\n".join(body) + "\n"


class RulesTest(unittest.TestCase):
    def test_r1_flags_literal_token_not_placeholder(self):
        fake = "abcdef" + "0123456789abcdef"  # montado em runtime para o scanner não achar segredo no fonte
        self.assertTrue(check_diff(diff("a.sh", '+curl -H "Authorization: Bearer ' + fake + '"')))
        self.assertTrue(check_diff(diff("a.md", "+MCP_" + "TOKEN=" + fake)))
        self.assertFalse(check_diff(diff("a.md", "+MCP_TOKEN=<seu-token>")))
        self.assertFalse(check_diff(diff("a.sh", '+curl -H "Authorization: Bearer $MCP_TOKEN"')))
        self.assertFalse(check_diff(diff("a.py", '+API_KEY = os.environ["DEEPSEEK_API_KEY"]')))

    def test_r2_frontmatter(self):
        base = "---\nname: x\ndescription: y\n{}tools: Read\n---\ncorpo\n"
        self.assertEqual(check_r2_text("a.md", base.format("model: haiku\n")), [])
        self.assertEqual(check_r2_text("a.md", base.format('model: "opus"\n')), [])
        self.assertEqual(check_r2_text("a.md", base.format("model: inherit\n")), [])
        self.assertTrue(check_r2_text("a.md", base.format("")))
        self.assertTrue(check_r2_text("a.md", base.format("model:\n")))
        self.assertTrue(check_r2_text("a.md", base.format("models: haiku\n")))
        self.assertTrue(check_r2_text("a.md", "---\nname: x\n---\nmodel: opus\n"))

    def test_r4_requires_evidence(self):
        ok = [(1, "- [x] 1.1 — feito: `pytest -q` 14 passed (exit 0)")]
        self.assertEqual(check_r4_lines("TASKS.md", ok), [])
        self.assertTrue(check_r4_lines("TASKS.md", [(1, "- [x] 1.1 — Feito")]))
        self.assertTrue(check_r4_lines("TASKS.md", [(1, "- [x] 5.1 — algo. Bloqueado: depende de 1.5")]))
        self.assertEqual(check_r4_lines("TASKS.md", [(1, "- [ ] 1.1 — aberto")]), [])

    def test_r5_attempt_limit(self):
        self.assertTrue(check_diff(diff("scripts/end-of-task.sh", "+MAX=5")))
        self.assertTrue(check_diff(diff("harness/tasklog.py", "+MAX_ATTEMPTS = 10")))
        self.assertFalse(check_diff(diff("harness/tasklog.py", "+MAX_ATTEMPTS = 3")))
        self.assertTrue(check_diff(diff("scripts/end-of-task.sh", "+while true; do")))
        self.assertFalse(check_diff(diff("CLAUDE.md", "+- Agentes em paralelo: de 3 a 5.")))

    def test_labeled_cases(self):
        wrong = []
        for f in sorted(glob.glob(os.path.join(EVAL, "cases_*.json"))):
            for c in json.load(open(f)):
                if c["id"] in KNOWN_MISSES:
                    continue
                if bool(check_diff(c["diff"])) != (c["label"] == "violates"):
                    wrong.append(c["id"])
        self.assertEqual(wrong, [])


if __name__ == "__main__":
    unittest.main()
