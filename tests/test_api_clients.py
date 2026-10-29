import contextlib
import io
import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from harness import higgsfield, llm

# chaves falsas montadas em runtime: o scanner de segredos do repo não deve achar nada no fonte
DS = "sk-" + "d" * 20
OR = "sk-or-" + "v1-" + "o" * 20
CF = "cf" + "T" * 30
HF = "hf" + "K" * 20
ENV_NAMES = ("DEEPSEEK_API_KEY", "DEEP_SEEK_API_KEY", "DEEPSEEK_PROVIDER", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
             "JEV_API_KEY", "JEV_PROVIDER", "JEV_BASE_URL", "JEV_MODEL", "CLOUDFLARE_ACCOUNT_ID", "CF_ACCOUNT_ID",
             "HIGGSFIELD_API_KEY", "HIGGSFIELD_BASE_URL")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Handler(BaseHTTPRequestHandler):
    log = []
    polls = 0

    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _record(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"null") if n else None
        Handler.log.append({"method": self.command, "path": self.path, "headers": dict(self.headers), "body": body})
        return body

    def do_POST(self):
        self._record()
        p = self.path
        if p.endswith("/e402/chat/completions"):
            return self._send(402, {"error": "Insufficient Balance"})
        if p.endswith("/e401/chat/completions"):
            return self._send(401, {"error": "bad key " + self.headers["Authorization"]})
        if "/diffok/" in p:
            txt = "Aqui está:\n```diff\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-ola mundo\n+ola harness\n```\nFeito."
            return self._send(200, {"choices": [{"message": {"content": txt}}], "usage": {}})
        if "/nodiff/" in p:
            return self._send(200, {"choices": [{"message": {"content": "não sei fazer isso"}}], "usage": {}})
        if p.endswith("/chat/completions"):
            return self._send(200, {"choices": [{"message": {"content": "<think>pensando</think>\n\nola"}}], "usage": {"total_tokens": 5}})
        if p.endswith("/jevfail"):
            return self._send(200, {"success": False, "errors": [{"code": 7003, "message": "User Input Error"}]})
        if p.endswith("/jev"):
            return self._send(200, {"success": True, "result": {"state": "Completed", "result": {
                "model": "jev-1.13.0", "answers": {"urgente": {"type": "noul", "noul": 0.9}}}}})
        if p == "/higgsfield-ai/soul/v2/standard":
            return self._send(200, {"request_id": "req-1"})
        if p == "/e402/model":
            return self._send(402, {"error": "no credits"})
        if p.endswith("/cancel"):
            return self._send(200, {})
        self._send(404, {"error": "rota desconhecida " + p})

    def do_GET(self):
        self._record()
        if self.path == "/requests/req-1/status":
            Handler.polls += 1
            if Handler.polls < 2:
                return self._send(200, {"status": "queued"})
            return self._send(200, {"status": "completed", "images": [{"url": "https://exemplo/img.png"}]})
        self._send(404, {})


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        Handler.log, Handler.polls = [], 0
        patcher = mock.patch.dict(os.environ, {"KURU_POLL_SECONDS": "0"})
        patcher.start()
        self.addCleanup(patcher.stop)
        for n in ENV_NAMES:
            os.environ.pop(n, None)

    def run_cli(self, fn, args, **env):
        os.environ.update(env)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fn(args)
        return code, out.getvalue(), err.getvalue()

    # ---------- DeepSeek (qualquer provedor) ----------
    def test_deepseek_key_sends_bearer_model_and_strips_think(self):
        code, out, _ = self.run_cli(llm.deepseek_main, ["--prompt", "oi", "--system", "seja breve"],
                                    DEEPSEEK_API_KEY=DS, DEEPSEEK_BASE_URL=self.base + "/ok")
        self.assertEqual((code, out.strip()), (0, "ola"))
        req = Handler.log[0]
        self.assertEqual(req["path"], "/ok/chat/completions")
        self.assertEqual(req["headers"]["Authorization"], f"Bearer {DS}")
        self.assertEqual(req["body"]["model"], "deepseek-chat")
        self.assertEqual([m["role"] for m in req["body"]["messages"]], ["system", "user"])

    def test_openrouter_key_picks_openrouter_model_and_model_override_wins(self):
        self.run_cli(llm.deepseek_main, ["--prompt", "oi"], DEEPSEEK_API_KEY=OR, DEEPSEEK_BASE_URL=self.base + "/ok")
        self.assertEqual(Handler.log[0]["body"]["model"], "deepseek/deepseek-v3.2")
        self.run_cli(llm.deepseek_main, ["--prompt", "oi"], DEEPSEEK_MODEL="deepseek/deepseek-v4-flash")
        self.assertEqual(Handler.log[1]["body"]["model"], "deepseek/deepseek-v4-flash")

    def test_alias_name_works(self):
        code, out, err = self.run_cli(llm.deepseek_main, ["--dry-run"], DEEP_SEEK_API_KEY=DS)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["provider"], "deepseek")

    def test_provider_detection(self):
        self.assertEqual(llm.detect_provider(DS), "deepseek")
        self.assertEqual(llm.detect_provider(OR), "openrouter")
        self.assertEqual(llm.detect_provider(DS, "openrouter"), "openrouter")
        with self.assertRaises(llm.ConfigError):
            llm.detect_provider(DS, "outro")
        with self.assertRaises(llm.ConfigError):
            llm.detect_provider(CF)  # chave sem prefixo de deepseek/openrouter (ex.: token da Cloudflare)

    def test_dry_run_never_prints_the_key(self):
        _, out, err = self.run_cli(llm.deepseek_main, ["--dry-run"], DEEPSEEK_API_KEY=DS)
        self.assertNotIn(DS, out + err)
        self.assertIn("caracteres", out)

    def test_balance_error_is_76_and_bad_key_is_3_without_leaking_the_key(self):
        code, _, err = self.run_cli(llm.deepseek_main, ["--prompt", "oi"], DEEPSEEK_API_KEY=DS, DEEPSEEK_BASE_URL=self.base + "/e402")
        self.assertEqual(code, 76)
        self.assertIn("saldo", err)
        code, _, err = self.run_cli(llm.deepseek_main, ["--prompt", "oi"], DEEPSEEK_API_KEY=DS, DEEPSEEK_BASE_URL=self.base + "/e401")
        self.assertEqual(code, 3)
        self.assertNotIn(DS, err)
        self.assertIn("***", err)

    def test_no_key_is_config_error(self):
        code, out, err = self.run_cli(llm.deepseek_main, ["--prompt", "oi"])
        self.assertEqual((code, out), (2, ""))
        self.assertIn("DEEPSEEK_API_KEY", err)
        self.assertEqual(Handler.log, [])

    # ---------- DeepSeek: --diff-out e --out ----------
    def repo_with(self, content):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        old = os.getcwd()
        os.chdir(d.name)
        self.addCleanup(os.chdir, old)
        subprocess.run(["git", "init", "-q"], check=True)
        with open("a.txt", "w") as f:
            f.write(content)
        return d.name

    def test_diff_out_extracts_block_and_validates_with_git_apply(self):
        self.repo_with("ola mundo\n")
        code, out, err = self.run_cli(llm.deepseek_main, ["--prompt", "troque", "--diff-out", ".kuru/t.diff"],
                                      DEEPSEEK_API_KEY=DS, DEEPSEEK_BASE_URL=self.base + "/diffok")
        self.assertEqual(code, 0, err)
        res = json.loads(out)
        self.assertEqual((res["git_apply_check"], res["diff"], res["provedor"]), ("ok", ".kuru/t.diff", "deepseek"))
        diff = read(".kuru/t.diff")
        self.assertTrue(diff.startswith("--- a/a.txt") and diff.endswith("+ola harness\n"))
        self.assertNotIn("```", diff)
        self.assertEqual(read("a.txt"), "ola mundo\n")  # só valida, nunca aplica

    def test_diff_out_exit_4_when_diff_does_not_apply_or_is_missing(self):
        self.repo_with("conteudo diferente\n")
        code, out, _ = self.run_cli(llm.deepseek_main, ["--prompt", "x", "--diff-out", "t.diff"],
                                    DEEPSEEK_API_KEY=DS, DEEPSEEK_BASE_URL=self.base + "/diffok")
        self.assertEqual(code, 4)
        self.assertNotEqual(json.loads(out)["git_apply_check"], "ok")
        code, out, err = self.run_cli(llm.deepseek_main, ["--prompt", "x", "--diff-out", "t2.diff"],
                                      DEEPSEEK_API_KEY=DS, DEEPSEEK_BASE_URL=self.base + "/nodiff")
        self.assertEqual((code, out), (4, ""))
        self.assertIn("diff unificado", err)
        self.assertFalse(os.path.exists("t2.diff"))

    def test_out_writes_file_instead_of_printing_the_answer(self):
        self.repo_with("x\n")
        code, out, _ = self.run_cli(llm.deepseek_main, ["--prompt", "oi", "--out", ".kuru/r.txt"],
                                    DEEPSEEK_API_KEY=DS, DEEPSEEK_BASE_URL=self.base + "/ok")
        self.assertEqual(code, 0)
        self.assertEqual(read(".kuru/r.txt").strip(), "ola")
        self.assertEqual(json.loads(out)["saida"], ".kuru/r.txt")

    def test_extract_diff_variants(self):
        d = "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n"
        self.assertEqual(llm.extract_diff("texto\n```diff\n" + d + "```\nfim"), d)
        self.assertEqual(llm.extract_diff("```\n" + d + "```"), d)
        self.assertEqual(llm.extract_diff(d), d)
        self.assertEqual(llm.extract_diff("```python\nprint(1)\n```"), "")

    # ---------- Jev ----------
    def jev_args(self, questions):
        return ["--state", "checkout fora do ar", "--questions", json.dumps(questions)]

    def test_jev_sends_model_and_input_and_returns_answers(self):
        q = {"urgente": {"type": "noul", "instructions": "É urgente?"}}
        code, out, err = self.run_cli(llm.jev_main, self.jev_args(q), JEV_API_KEY=CF, JEV_BASE_URL=self.base + "/jev")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["result"]["answers"]["urgente"]["noul"], 0.9)
        req = Handler.log[0]
        self.assertEqual(req["headers"]["Authorization"], f"Bearer {CF}")
        self.assertEqual(req["body"], {"model": "typesafe/jev", "input": {"state": "checkout fora do ar", "questions": q}})

    def test_jev_rejects_bad_format_before_calling_the_api(self):
        bad = [
            {"ping": "responda pong"},
            {"x": {"type": "talvez", "instructions": "?"}},
            {"x": {"type": "noul"}},
            {"x": {"type": "choice", "instructions": "?"}},
            {"x": {"type": "score", "instructions": "?", "criteria": {"a": "b", "c": "d"}}},
        ]
        for q in bad:
            with self.subTest(q=q):
                code, _, err = self.run_cli(llm.jev_main, self.jev_args(q), JEV_API_KEY=CF, JEV_BASE_URL=self.base + "/jev")
                self.assertEqual(code, 2, err)
        self.assertEqual(Handler.log, [])

    def test_jev_provider_failure_is_3_and_openrouter_key_is_explained(self):
        q = {"x": {"type": "noul", "instructions": "?"}}
        code, _, err = self.run_cli(llm.jev_main, self.jev_args(q), JEV_API_KEY=CF, JEV_BASE_URL=self.base + "/jevfail")
        self.assertEqual(code, 3)
        self.assertIn("7003", err)
        code, _, err = self.run_cli(llm.jev_main, ["--dry-run"], JEV_API_KEY=OR)
        self.assertEqual(code, 2)
        self.assertIn("Workers AI", err)

    def test_jev_example_is_valid(self):
        code, out, _ = self.run_cli(llm.jev_main, ["--example"])
        ex = json.loads(out)
        self.assertEqual(code, 0)
        llm.validate_jev_input(ex["state"], ex["questions"])

    # ---------- Higgsfield ----------
    def hf(self, args, **env):
        env.setdefault("HIGGSFIELD_API_KEY", HF)
        env.setdefault("HIGGSFIELD_BASE_URL", self.base)
        return self.run_cli(higgsfield.main, args, **env)

    def test_higgsfield_run_requires_yes_and_sends_nothing(self):
        code, _, err = self.hf(["run", "/higgsfield-ai/soul/v2/standard", "--body", '{"prompt":"gato"}'])
        self.assertEqual(code, 2)
        self.assertIn("--yes", err)
        self.assertEqual(Handler.log, [])

    def test_higgsfield_run_polls_until_done_and_uses_key_scheme(self):
        code, out, err = self.hf(["run", "/higgsfield-ai/soul/v2/standard", "--body", '{"prompt":"gato"}', "--yes"])
        self.assertEqual(code, 0, err)
        res = json.loads(out)
        self.assertEqual((res["request_id"], res["status"], res["images"]), ("req-1", "completed", ["https://exemplo/img.png"]))
        post = Handler.log[0]
        self.assertEqual(post["headers"]["Authorization"], f"Key {HF}")
        self.assertIn("Idempotency-Key", post["headers"])
        self.assertEqual(post["body"], {"prompt": "gato"})
        self.assertGreaterEqual(Handler.polls, 2)

    def test_higgsfield_rejects_bad_endpoint_and_missing_key(self):
        for ep in ("http://evil.example/x", "/a/../b", "sem-barra"):
            with self.subTest(ep=ep):
                self.assertEqual(self.hf(["run", ep, "--body", "{}", "--yes"])[0], 2)
        self.assertEqual(Handler.log, [])
        os.environ.pop("HIGGSFIELD_API_KEY", None)
        code, _, err = self.run_cli(higgsfield.main, ["status", "req-1"])
        self.assertEqual(code, 2)
        self.assertIn("HIGGSFIELD_API_KEY", err)

    def test_higgsfield_status_cancel_and_balance_error(self):
        Handler.polls = 5
        code, out, _ = self.hf(["status", "req-1"])
        self.assertEqual((code, json.loads(out)["status"]), (0, "completed"))
        code, out, _ = self.hf(["cancel", "req-1"])
        self.assertEqual((code, json.loads(out)["cancelamento"]), (0, "enviado"))
        code, _, err = self.hf(["run", "/e402/model", "--body", "{}", "--yes"])
        self.assertEqual(code, 76)


if __name__ == "__main__":
    unittest.main()
