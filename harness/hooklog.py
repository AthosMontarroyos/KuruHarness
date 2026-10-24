"""Registro automático do hook Stop no log por tarefa (Fase 6, tarefa 6.2).

Chamado por scripts/end-of-task.sh ao fim de uma tarefa (verificação verde, ou limite de
tentativas atingido). Modelo e tokens vêm do transcript da sessão, que o Claude Code passa ao
hook em `transcript_path`. Esse formato NÃO é uma API estável: a leitura é defensiva e, se
falhar, grava model "unknown" e tokens 0. Nunca levanta erro para o hook.

Limites conhecidos: só conta o transcript principal (sub-agents têm transcripts próprios) e
os tokens são o delta desde o último registro da mesma sessão.
"""
import argparse
import collections
import json
import os
import sys
import uuid
from pathlib import Path

from harness.tasklog import DEFAULT_PATH, append_record

MARK = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude/state/tokens_mark.json"


def read_usage(transcript_path):
    """(modelo mais usado, tokens_in, tokens_out, tokens_cache) acumulados no transcript.

    tokens_in = entrada nova (input + criação de cache); tokens_cache = leitura de cache, que
    domina a soma (cada turno relê o contexto) e distorce qualquer estimativa de custo.
    """
    models, tin, tout, tcache = collections.Counter(), 0, 0, 0
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                try:
                    msg = json.loads(line).get("message") or {}
                except (json.JSONDecodeError, AttributeError):
                    continue
                usage = msg.get("usage")
                if msg.get("role") != "assistant" or not isinstance(usage, dict):
                    continue
                tin += sum(int(usage.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens"))
                tcache += int(usage.get("cache_read_input_tokens") or 0)
                tout += int(usage.get("output_tokens") or 0)
                if msg.get("model"):
                    models[msg["model"]] += 1
    except (OSError, ValueError, TypeError):
        return "unknown", 0, 0, 0
    return (models.most_common(1)[0][0] if models else "unknown"), tin, tout, tcache


def log_stop(result, attempts, hook_input="", log_path=DEFAULT_PATH, mark_path=MARK, task_id=None):
    try:
        data = json.loads(hook_input) if hook_input.strip() else {}
    except json.JSONDecodeError:
        data = {}
    session = str(data.get("session_id") or "nosession")
    model, tin, tout, tcache = read_usage(data["transcript_path"]) if data.get("transcript_path") else ("unknown", 0, 0, 0)

    try:
        marks = json.loads(Path(mark_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        marks = {}
    prev = {"in": 0, "out": 0, "cache": 0, **marks.get(session, {})}
    d_in, d_out, d_cache = max(0, tin - prev["in"]), max(0, tout - prev["out"]), max(0, tcache - prev["cache"])
    marks[session] = {"in": tin, "out": tout, "cache": tcache}

    rec = append_record(
        task_id or os.environ.get("KURU_TASK_ID") or f"{session[:8]}-{uuid.uuid4().hex[:6]}",
        model, d_in, d_out, result, attempts, path=log_path, tokens_cache=d_cache,
    )
    Path(mark_path).parent.mkdir(parents=True, exist_ok=True)
    Path(mark_path).write_text(json.dumps(marks), encoding="utf-8")
    return rec


def main(argv=None):
    p = argparse.ArgumentParser(prog="harness.hooklog")
    p.add_argument("--result", required=True, choices=["ok", "fail"])
    p.add_argument("--attempts", required=True, type=int)
    args = p.parse_args(argv)
    try:
        log_stop(args.result, args.attempts, os.environ.get("HOOK_INPUT", ""))
    except Exception as e:  # o log nunca pode derrubar o hook
        print(f"hooklog ignorado: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
