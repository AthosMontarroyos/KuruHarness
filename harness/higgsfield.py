"""Higgsfield (imagem e vídeo) por API, sem MCP: `kuru higgsfield run|status|cancel`.

Chave em HIGGSFIELD_API_KEY (vai como `Authorization: Key <chave>`; se a sua for `id:segredo`, use o valor inteiro).
`run` GASTA crédito: sem `--yes` ele só mostra o que faria e sai com 2. Confirme com o usuário antes de usar `--yes`.
Saídas: 0 ok | 2 configuração/entrada inválida | 3 erro do provedor | 76 saldo/limite esgotado.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

DONE = ("completed", "failed", "nsfw", "canceled", "cancelled")
WAITING = ("queued", "in_progress")


class HFError(Exception):
    def __init__(self, msg, code=3):
        super().__init__(msg)
        self.code = code


def _key():
    key = (os.environ.get("HIGGSFIELD_API_KEY") or "").strip()
    if not key:
        raise HFError("defina HIGGSFIELD_API_KEY", 2)
    return key


def _call(method, path, body=None):
    key = _key()
    base = os.environ.get("HIGGSFIELD_BASE_URL", "https://api.higgsfield.ai").rstrip("/")
    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json", "User-Agent": "kuru-harness"}
    if method == "POST" and body is not None:
        headers["Idempotency-Key"] = str(uuid.uuid4())
    req = urllib.request.Request(base + path, method=method, headers=headers,
                                 data=json.dumps(body).encode("utf-8") if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=float(os.environ.get("KURU_HTTP_TIMEOUT", "60"))) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")[:500].replace(key, "***")
        code = 76 if e.code in (402, 429) else 3
        raise HFError(f"HTTP {e.code}: {text}", code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise HFError(f"sem conexão com a Higgsfield: {str(e).replace(key, '***')}")
    except json.JSONDecodeError:
        raise HFError("resposta da Higgsfield não é JSON")


def check_endpoint(ep):
    if not isinstance(ep, str) or not ep.startswith("/") or ".." in ep or "://" in ep:
        raise HFError("endpoint inválido: use um caminho como /provedor/modelo/versao (começa com /, sem host nem ..)", 2)


def summarize(st, request_id):
    out = {"request_id": request_id, "status": st.get("status"), "error": st.get("error")}
    if st.get("images"):
        out["images"] = [i.get("url") for i in st["images"] if isinstance(i, dict)]
    if isinstance(st.get("video"), dict):
        out["video"] = st["video"].get("url")
    return out


def wait_done(request_id, max_seconds):
    poll = float(os.environ.get("KURU_POLL_SECONDS", "3"))
    start = time.time()
    st = _call("GET", f"/requests/{request_id}/status")
    while st.get("status") in WAITING and time.time() - start < max_seconds:
        time.sleep(poll)
        st = _call("GET", f"/requests/{request_id}/status")
    return st


def main(argv=None):
    p = argparse.ArgumentParser(prog="kuru higgsfield")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="envia um pedido a QUALQUER modelo (GASTA crédito)")
    r.add_argument("endpoint", help="ex.: /higgsfield-ai/soul/v2/standard")
    r.add_argument("--body", help="JSON do corpo, exatamente como o schema do modelo")
    r.add_argument("--body-file")
    r.add_argument("--wait", type=int, default=40, help="segundos esperando terminar (padrão 40)")
    r.add_argument("--yes", action="store_true", help="o usuário aprovou o gasto")
    s = sub.add_parser("status")
    s.add_argument("request_id")
    c = sub.add_parser("cancel")
    c.add_argument("request_id")
    a = p.parse_args(argv)
    try:
        if a.cmd == "run":
            check_endpoint(a.endpoint)
            raw = a.body if a.body is not None else (open(a.body_file, encoding="utf-8").read() if a.body_file else None)
            if raw is None:
                raise HFError("informe --body ou --body-file com o JSON do modelo", 2)
            try:
                body = json.loads(raw)
            except json.JSONDecodeError as e:
                raise HFError(f"--body não é JSON válido: {e}", 2)
            if not a.yes:
                print(json.dumps({"nao_enviado": True, "motivo": "falta --yes: isto gasta crédito, confirme com o usuário",
                                  "endpoint": a.endpoint, "body": body}, ensure_ascii=False), file=sys.stderr)
                return 2
            sub_resp = _call("POST", a.endpoint, body)
            rid = sub_resp.get("request_id")
            if not rid:
                raise HFError(f"resposta sem request_id: {json.dumps(sub_resp)[:300]}")
            print(json.dumps(summarize(wait_done(rid, a.wait), rid), ensure_ascii=False))
        elif a.cmd == "status":
            print(json.dumps(summarize(_call("GET", f"/requests/{a.request_id}/status"), a.request_id), ensure_ascii=False))
        else:
            _call("POST", f"/requests/{a.request_id}/cancel", {})
            print(json.dumps({"request_id": a.request_id, "cancelamento": "enviado"}))
    except HFError as e:
        print(f"erro: {e}", file=sys.stderr)
        return e.code
    except OSError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
