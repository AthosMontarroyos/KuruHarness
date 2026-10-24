"""Chamadas diretas por API, sem MCP, sem plugin e sem comandos: DeepSeek e Jev.

A chave vem de variável de ambiente e pode ser de provedores diferentes:
  DEEPSEEK_API_KEY (ou DEEP_SEEK_API_KEY): chave do DeepSeek, do OpenRouter (sk-or-...) ou do Workers AI.
  JEV_API_KEY: chave do Workers AI (o Jev estruturado, `typesafe/jev`, só existe lá).
  CLOUDFLARE_ACCOUNT_ID: obrigatório quando a chave é do Workers AI.
Opcionais: *_PROVIDER (deepseek | openrouter | workers-ai), *_BASE_URL, *_MODEL.

Saídas: 0 ok | 2 configuração/entrada inválida | 3 erro do provedor | 76 saldo ou limite esgotado.
A chave nunca é impressa.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEEPSEEK_KEYS = ("DEEPSEEK_API_KEY", "DEEP_SEEK_API_KEY")
ACCOUNT_KEYS = ("CLOUDFLARE_ACCOUNT_ID", "CF_ACCOUNT_ID")
PROVIDERS = ("deepseek", "openrouter", "workers-ai")
DEFAULT_MODEL = {
    "deepseek": "deepseek-chat",
    "openrouter": "deepseek/deepseek-v3.2",
    "workers-ai": "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",  # roda no plano gratuito; o v4 exige plano pago
}
JEV_TYPES = ("noul", "choice", "score")
JEV_EXAMPLE = {
    "state": "Checkout fora do ar há 1 hora para todos os clientes.",
    "questions": {
        "urgente": {"type": "noul", "instructions": "Isto é urgente?"},
        "time": {"type": "choice", "instructions": "Qual time cuida disto?",
                 "criteria": {"billing": "Pagamentos e cobrança", "technical": "Quedas e erros"}},
        "gravidade": {"type": "score", "instructions": "Quão grave é?", "criteria": ["Baixa", "Média", "Alta"]},
    },
}


class ConfigError(Exception):
    """Falta chave/variável ou a entrada está fora do formato (saída 2)."""


class ProviderError(Exception):
    def __init__(self, msg, code=3):
        super().__init__(msg)
        self.code = code


def first_env(names, env):
    for n in names:
        if (env.get(n) or "").strip():
            return env[n].strip()
    return ""


def detect_provider(key, explicit=""):
    explicit = (explicit or "").strip().lower().replace("_", "-")
    if explicit:
        if explicit not in PROVIDERS:
            raise ConfigError(f"provedor desconhecido: {explicit} (use {', '.join(PROVIDERS)})")
        return explicit
    if key.startswith("sk-or-"):
        return "openrouter"
    if key.startswith("sk-"):
        return "deepseek"
    return "workers-ai"  # tokens da Cloudflare não têm prefixo fixo


def _account(env):
    acct = first_env(ACCOUNT_KEYS, env)
    if not acct:
        raise ConfigError("chave do Workers AI exige CLOUDFLARE_ACCOUNT_ID (o id da conta Cloudflare)")
    return acct


def resolve_deepseek(env=None):
    env = os.environ if env is None else env
    key = first_env(DEEPSEEK_KEYS, env)
    if not key:
        raise ConfigError("defina DEEPSEEK_API_KEY (chave do DeepSeek, do OpenRouter ou do Workers AI)")
    provider = detect_provider(key, env.get("DEEPSEEK_PROVIDER", ""))
    base = (env.get("DEEPSEEK_BASE_URL") or "").rstrip("/")
    if not base:
        if provider == "workers-ai":  # só este provedor precisa do id da conta
            base = f"https://api.cloudflare.com/client/v4/accounts/{_account(env)}/ai/v1"
        else:
            base = {"deepseek": "https://api.deepseek.com", "openrouter": "https://openrouter.ai/api/v1"}[provider]
    model = (env.get("DEEPSEEK_MODEL") or "").strip() or DEFAULT_MODEL[provider]
    return {"provider": provider, "url": base + "/chat/completions", "model": model, "key": key}


def resolve_jev(env=None):
    env = os.environ if env is None else env
    key = first_env(("JEV_API_KEY",), env)
    if not key:
        raise ConfigError("defina JEV_API_KEY (chave do Cloudflare Workers AI) e CLOUDFLARE_ACCOUNT_ID")
    provider = (env.get("JEV_PROVIDER") or "workers-ai").strip().lower().replace("_", "-")
    if provider == "openrouter" or key.startswith("sk-or-"):
        raise ConfigError("o OpenRouter só tem o Jev Router (um roteador de chat); o Jev estruturado "
                          "(`typesafe/jev`, com probabilidades) só existe no Workers AI. Use uma chave do Workers AI.")
    url = (env.get("JEV_BASE_URL") or "").rstrip("/") or f"https://api.cloudflare.com/client/v4/accounts/{_account(env)}/ai/run"
    return {"provider": "workers-ai", "url": url, "model": (env.get("JEV_MODEL") or "typesafe/jev").strip(), "key": key}


def validate_jev_input(state, questions):
    """Confere o formato ANTES de gastar uma chamada e explica o que está errado."""
    if not isinstance(state, str) or not state.strip():
        raise ConfigError("`state` deve ser um texto não vazio (o que será avaliado, por exemplo um diff)")
    if not isinstance(questions, dict) or not questions:
        raise ConfigError("`questions` deve ser um objeto {nome: {type, instructions, criteria?}}; veja `ask-jev --example`")
    for name, q in questions.items():
        if not isinstance(q, dict):
            raise ConfigError(f"pergunta '{name}': deve ser um objeto, não texto solto (texto solto dá erro 7003 no provedor)")
        if q.get("type") not in JEV_TYPES:
            raise ConfigError(f"pergunta '{name}': `type` deve ser um de {', '.join(JEV_TYPES)}")
        if not isinstance(q.get("instructions"), str) or not q["instructions"].strip():
            raise ConfigError(f"pergunta '{name}': falta `instructions` (a pergunta em si, com as regras no texto)")
        crit = q.get("criteria")
        if q["type"] == "choice" and not (isinstance(crit, dict) and len(crit) >= 2):
            raise ConfigError(f"pergunta '{name}': `choice` exige `criteria` como objeto {{opção: descrição}} com 2+ opções")
        if q["type"] == "score" and not (isinstance(crit, list) and len(crit) >= 2):
            raise ConfigError(f"pergunta '{name}': `score` exige `criteria` como lista ordenada com 2+ níveis")


def _redact(text, key):
    return text.replace(key, "***") if key else text


def http_json(url, key, payload, scheme="Bearer", timeout=None):
    timeout = timeout or float(os.environ.get("KURU_HTTP_TIMEOUT", "120"))
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"{scheme} {key}", "User-Agent": "kuru-harness"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = _redact(e.read().decode("utf-8", "replace")[:500], key)
        if e.code in (402, 429):
            raise ProviderError(f"saldo ou limite esgotado (HTTP {e.code}): {body}", 76)
        if e.code in (401, 403):
            raise ProviderError(f"chave recusada ou sem acesso (HTTP {e.code}): {body}")
        raise ProviderError(f"HTTP {e.code}: {body}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ProviderError(f"sem conexão com {url.split('/')[2]}: {_redact(str(e), key)}")
    except json.JSONDecodeError:
        raise ProviderError("resposta do provedor não é JSON")


def ask_deepseek(prompt, system="", max_tokens=None, env=None):
    cfg = resolve_deepseek(env)
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    payload = {"model": cfg["model"], "messages": messages, "stream": False}
    if max_tokens:
        payload["max_tokens"] = max_tokens
    data = http_json(cfg["url"], cfg["key"], payload)
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise ProviderError(f"resposta sem choices[0].message.content: {json.dumps(data)[:300]}")
    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S)  # modelos de raciocínio devolvem o pensamento
    return text.strip(), data.get("usage") or {}, cfg


def ask_jev(state, questions, env=None):
    validate_jev_input(state, questions)
    cfg = resolve_jev(env)
    data = http_json(cfg["url"], cfg["key"], {"model": cfg["model"], "input": {"state": state, "questions": questions}})
    if data.get("success") is False:
        raise ProviderError(f"Workers AI recusou: {json.dumps(data.get('errors'))[:400]}")
    return data.get("result", data), cfg


def _public(cfg):
    return {"provider": cfg["provider"], "url": cfg["url"], "model": cfg["model"], "key": f"definida ({len(cfg['key'])} caracteres)"}


def _fail(e):
    print(f"erro: {e}", file=sys.stderr)
    return e.code if isinstance(e, ProviderError) else 2


def deepseek_main(argv=None):
    p = argparse.ArgumentParser(prog="kuru ask-deepseek", description="Pergunta ao DeepSeek (qualquer provedor) e imprime a resposta.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--prompt")
    g.add_argument("--prompt-file")
    p.add_argument("--system", default="")
    p.add_argument("--max-tokens", type=int)
    p.add_argument("--dry-run", action="store_true", help="mostra provedor, URL e modelo sem chamar")
    a = p.parse_args(argv)
    try:
        if a.dry_run:
            print(json.dumps(_public(resolve_deepseek()), ensure_ascii=False))
            return 0
        prompt = a.prompt if a.prompt is not None else (open(a.prompt_file, encoding="utf-8").read() if a.prompt_file else sys.stdin.read())
        if not prompt.strip():
            raise ConfigError("prompt vazio (use --prompt, --prompt-file ou stdin)")
        text, usage, cfg = ask_deepseek(prompt, a.system, a.max_tokens)
    except (ConfigError, ProviderError, OSError) as e:
        return _fail(e)
    print(text)
    print(f"[{cfg['provider']} · {cfg['model']} · {usage}]", file=sys.stderr)
    return 0


def jev_main(argv=None):
    p = argparse.ArgumentParser(prog="kuru ask-jev", description="Avalia um estado contra perguntas tipadas (noul/choice/score).")
    p.add_argument("--state")
    p.add_argument("--state-file")
    p.add_argument("--questions", help="JSON {nome: {type, instructions, criteria?}}")
    p.add_argument("--questions-file")
    p.add_argument("--example", action="store_true", help="imprime um exemplo válido de entrada")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.example:
            print(json.dumps(JEV_EXAMPLE, ensure_ascii=False, indent=1))
            return 0
        if a.dry_run:
            print(json.dumps(_public(resolve_jev()), ensure_ascii=False))
            return 0
        state = a.state if a.state is not None else (open(a.state_file, encoding="utf-8").read() if a.state_file else None)
        raw = a.questions if a.questions is not None else (open(a.questions_file, encoding="utf-8").read() if a.questions_file else None)
        if state is None or raw is None:
            raise ConfigError("informe --state/--state-file e --questions/--questions-file (veja --example)")
        try:
            questions = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ConfigError(f"--questions não é JSON válido: {e}")
        result, _ = ask_jev(state, questions)
    except (ConfigError, ProviderError, OSError) as e:
        return _fail(e)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(deepseek_main())
