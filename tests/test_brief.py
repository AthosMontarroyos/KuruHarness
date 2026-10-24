import tempfile
import unittest
from pathlib import Path

from harness import brief

RULES_MD = "# CLAUDE.md\n\n## Regras para quem codifica (qualquer texto aqui é ignorado)\n- regra A do projeto\n- regra B do projeto\n\n## Outra seção\nnão entra\n"


class BriefTest(unittest.TestCase):
    def test_project_rules_come_from_the_projects_claude_md(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "CLAUDE.md"
            p.write_text(RULES_MD, encoding="utf-8")
            rules = brief.project_rules(str(p))
        self.assertEqual(rules, "- regra A do projeto\n- regra B do projeto")
        self.assertNotIn("não entra", rules)

    def test_kit_rules_are_the_fallback_and_nonempty(self):
        self.assertIn("3 tentativas", brief.project_rules("arquivo-que-nao-existe.md"))

    def test_brief_is_self_contained_and_explicit(self):
        text = brief.build("renomear x para y", ["a.py", "b.py"], "nenhuma referência a x", "bash bin/kuru unittest", rules="- regra A")
        for part in ("# Tarefa\nrenomear x para y", "- a.py\n- b.py", brief.RULES_MARKER, "- regra A", "# Como trabalhar",
                     "`bash bin/kuru unittest`", "nenhuma referência a x", "NÃO faça commit", "# Entrega"):
            self.assertIn(part, text)

    def test_brief_defaults_when_optional_parts_are_missing(self):
        text = brief.build("fazer algo", rules="- r")
        self.assertIn("nenhum arquivo indicado", text)
        self.assertIn("os testes e linters que o projeto tiver", text)
        self.assertIn("os testes passam e nenhum outro arquivo foi alterado", text)

    def test_empty_task_is_rejected(self):
        with self.assertRaises(brief.BriefError):
            brief.build("   ", rules="- r")

    def test_cli_writes_out_file_and_marker_satisfies_the_cursor_guard(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "sub" / "t.prompt"
            self.assertEqual(brief.main(["--task", "x", "--out", str(out)]), 0)
            self.assertIn(brief.RULES_MARKER, out.read_text(encoding="utf-8"))
        self.assertEqual(brief.main([]), 2)  # sem --task


if __name__ == "__main__":
    unittest.main()
