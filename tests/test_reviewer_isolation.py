import unittest
from pathlib import Path

from harness.check_rules import _frontmatter

AGENTS = Path(__file__).resolve().parent.parent / ".claude" / "agents"


class ReviewerIsolationTest(unittest.TestCase):
    """Regra 3 do SPEC: o revisor só vê o pacote (diff + regras), nunca o projeto."""

    def test_reviewers_have_no_tools_and_omit_claude_md(self):
        for name in ("reviewer", "reviewer-senior"):
            with self.subTest(agent=name):
                fm = _frontmatter((AGENTS / f"{name}.md").read_text(encoding="utf-8"))
                self.assertIsNotNone(fm)
                self.assertIn("tools: []", [l.strip() for l in fm])
                self.assertIn("omitClaudeMd: true", [l.strip() for l in fm])


if __name__ == "__main__":
    unittest.main()
