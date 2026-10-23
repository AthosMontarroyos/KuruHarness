"""Log por tarefa (Fase 6): um registro JSONL por tarefa, com resumo por modelo."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude/state/tasks.jsonl"
VALID_RESULTS = {"ok", "fail"}
MAX_ATTEMPTS = 3


def validate(rec):
    if not rec.get("task_id") or not rec.get("model"):
        raise ValueError("task_id e model são obrigatórios")
    if rec.get("result") not in VALID_RESULTS:
        raise ValueError(f"result deve ser um de {sorted(VALID_RESULTS)}")
    attempts = rec.get("attempts")
    if not isinstance(attempts, int) or isinstance(attempts, bool) or not 1 <= attempts <= MAX_ATTEMPTS:
        raise ValueError(f"attempts deve ser inteiro entre 1 e {MAX_ATTEMPTS}")
    for key in ("tokens_in", "tokens_out", "tokens_cache"):
        v = rec.get(key, 0)  # tokens_cache é opcional (registros antigos não têm)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            raise ValueError(f"{key} deve ser inteiro >= 0")


def append_record(task_id, model, tokens_in, tokens_out, result, attempts, path=DEFAULT_PATH, ts=None, tokens_cache=0):
    rec = {
        "ts": ts or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task_id": task_id,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_cache": tokens_cache,
        "result": result,
        "attempts": attempts,
    }
    validate(rec)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def summarize(path=DEFAULT_PATH):
    """Devolve {model: {count, tokens_in, tokens_out, success_rate, avg_attempts}}.

    Linhas inválidas são ignoradas e contadas em result["_skipped"] quando houver.
    """
    path = Path(path)
    if not path.exists():
        return {}
    acc, skipped = {}, 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            validate(rec)
        except (ValueError, AttributeError):
            skipped += 1
            continue
        a = acc.setdefault(rec["model"], {"count": 0, "tokens_in": 0, "tokens_out": 0, "tokens_cache": 0, "ok": 0, "attempts": 0})
        a["count"] += 1
        a["tokens_in"] += rec["tokens_in"]
        a["tokens_out"] += rec["tokens_out"]
        a["tokens_cache"] += rec.get("tokens_cache", 0)
        a["ok"] += rec["result"] == "ok"
        a["attempts"] += rec["attempts"]
    out = {
        m: {
            "count": a["count"],
            "tokens_in": a["tokens_in"],
            "tokens_out": a["tokens_out"],
            "tokens_cache": a["tokens_cache"],
            "success_rate": round(a["ok"] / a["count"], 3),
            "avg_attempts": round(a["attempts"] / a["count"], 3),
        }
        for m, a in acc.items()
    }
    if skipped:
        out["_skipped"] = skipped
    return out


def main(argv=None):
    p = argparse.ArgumentParser(prog="harness.tasklog")
    sub = p.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("--task-id", required=True)
    add.add_argument("--model", required=True)
    add.add_argument("--tokens-in", type=int, required=True)
    add.add_argument("--tokens-out", type=int, required=True)
    add.add_argument("--tokens-cache", type=int, default=0)
    add.add_argument("--result", choices=sorted(VALID_RESULTS), required=True)
    add.add_argument("--attempts", type=int, required=True)
    add.add_argument("--path", default=DEFAULT_PATH)
    summ = sub.add_parser("summary")
    summ.add_argument("--path", default=DEFAULT_PATH)
    summ.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if args.cmd == "add":
        try:
            append_record(args.task_id, args.model, args.tokens_in, args.tokens_out,
                          args.result, args.attempts, path=args.path, tokens_cache=args.tokens_cache)
        except ValueError as e:
            print(f"erro: {e}", file=sys.stderr)
            return 1
        return 0

    data = summarize(args.path)
    if args.json:
        print(json.dumps(data, ensure_ascii=False))
    else:
        for m, s in data.items():
            if m == "_skipped":
                print(f"linhas ignoradas: {s}")
                continue
            print(f"{m}: n={s['count']} in={s['tokens_in']} out={s['tokens_out']} cache={s['tokens_cache']} "
                  f"ok={s['success_rate']} tentativas={s['avg_attempts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
