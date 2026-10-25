import unittest

from harness import route


class RouteTest(unittest.TestCase):
    def test_one_file_trivial(self):
        r = route.classify("renomear variável", ["a.py"])
        self.assertEqual((r["tier"], r["acao"], r["agents"]), ("trivial", "direto", []))  # delegar custa mais que fazer
        self.assertFalse(r["incerta"])

    def test_few_files_media(self):
        r = route.classify("adicionar função de resumo", ["a.py", "b.py"])
        self.assertEqual((r["tier"], r["acao"], r["agents"]), ("media", "direto", []))
        self.assertIn("6 arquivos", r["delegar_se"])
        self.assertNotIn("delegar_se", route.classify("renomear variável", ["a.py"]))

    def test_many_files_or_architecture_is_complex(self):
        self.assertEqual(route.classify("ajustar", ["a", "b", "c", "d"])["tier"], "complexa")
        self.assertEqual(route.classify("refatorar a arquitetura", ["a"])["agents"], ["planner", "implementer-sonnet"])

    def test_complex_plus_risk_becomes_long(self):
        r = route.classify("refatorar o módulo de pagamentos para nova arquitetura", ["a"])
        self.assertEqual((r["tier"], r["risco"]), ("longa", True))

    def test_long_task_goes_to_planner_then_parallel_sonnet(self):
        r = route.classify("reescrever o parser do zero", ["a"])
        self.assertEqual(r["agents"], ["planner", "implementer-sonnet"])
        self.assertIn("paralelo", r)
        self.assertEqual(route.classify("mexer", [f"f{i}" for i in range(9)])["tier"], "longa")

    def test_long_task_has_coder_chain_and_skips_deepseek_when_risky(self):
        normal = route.classify("reescrever o parser do zero", ["a"])
        self.assertEqual(normal["cadeia"], ["planner", "implementer-sonnet", "deepseek"])
        risky = route.classify("reescrever o parser de tokens do zero", ["a"])
        self.assertTrue(risky["risco"])
        self.assertNotIn("deepseek", risky["cadeia"])
        self.assertNotIn("cadeia", route.classify("corrigir typo", ["a.md"]))

    def test_risk_raises_one_tier_with_floor_media(self):
        base = route.classify("corrigir typo no texto", ["a.md"])
        self.assertEqual(base["tier"], "trivial")
        risky = route.classify("corrigir typo no texto do fluxo de auth", ["a.md"])
        self.assertEqual((risky["tier"], risky["risco"]), ("media", True))
        self.assertEqual(route.classify("apagar produção", ["a"])["tier"], "media")
        for palavra in ("pagamentos", "deploys", "credenciais", "tokens", "segredos"):
            self.assertTrue(route.classify(f"ajustar {palavra}", ["a"])["risco"], palavra)

    def test_no_signals_is_uncertain_media(self):
        r = route.classify("melhorar o projeto")
        self.assertEqual((r["tier"], r["incerta"]), ("media", True))

    def test_jev_can_only_raise_the_tier(self):
        r = route.classify("ajustar coisa", ["a", "b"])  # media
        up = route.apply_jev(r, {"choice": "complexa", "probabilities": {"complexa": 0.95}})
        self.assertEqual(up["tier"], "complexa")
        down = route.apply_jev(r, {"choice": "trivial", "probabilities": {"trivial": 0.99}})
        self.assertEqual(down["tier"], "media")
        weak = route.apply_jev(r, {"choice": "complexa", "probabilities": {"complexa": 0.6}})
        self.assertEqual(weak["tier"], "media")

    def test_counts_files_written_in_the_description(self):
        r = route.classify("cache com TTL compartilhado pelos 9 módulos")
        self.assertEqual(r["tier"], "longa")
        self.assertIn("9 arquivo(s)", r["motivos"])
        self.assertEqual(route.classify("ajustar 2 arquivos de config")["acao"], "direto")

    def test_design_words_mean_complex(self):
        self.assertEqual(route.classify("projete um cache com decisão de design")["tier"], "complexa")

    def test_partial_files_list_does_not_hide_the_written_count(self):
        self.assertEqual(route.classify("mexer em 20 arquivos", ["a.py"])["tier"], "longa")
        self.assertEqual(route.classify("mexer em 2 arquivos", ["a.py", "b.py", "c.py", "d.py", "e.py"])["tier"], "complexa")

    def test_jev_questions_are_typed(self):
        q = route.jev_questions("x")["tier"]
        self.assertEqual(q["type"], "choice")
        self.assertIn("complexa", q["criteria"])


if __name__ == "__main__":
    unittest.main()
