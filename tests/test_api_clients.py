import contextlib
import io
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from harness import higgsfield, llm

# chaves falsas montadas em runtime: o scanner de segredos do repo não deve achar nada no fonte
OR = "sk-or-" + "v1-" + "o" * 20
CF = "cf" + "T" * 30
HF = "hf" + "K" * 20
ENV_NAMES = ("JEV_API_KEY", "JEV_PROVIDER", "JEV_BASE_URL", "JEV_MODEL", "CLOUDFLARE_ACCOUNT_ID", "CF_ACCOUNT_ID",
             "HIGGSFIELD_API_KEY", "HIGGSFIELD_BASE_URL")


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
