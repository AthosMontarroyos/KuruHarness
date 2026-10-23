"""Fluxo de revisão da Fase 2: determinístico -> reviewer (Haiku) -> reviewer-senior (Opus).

O Opus só entra depois de 2 reprovações do Haiku na mesma tarefa. O total de
reprovações por tarefa respeita o limite de 3 tentativas (CLAUDE.md): na 3ª, PARAR.

    git diff | python3 -m harness.review_flow check  --task T1
    python3 -m harness.review_flow record --task T1 --stage reviewer --verdict REPROVADO
"""
import argparse
import json
import re
import sys
from pathlib import Path

from harness.check_rules import check_diff, parse_diff

STATE = Path(".claude/state/reviews.json")
MAX_ATTEMPTS = 3
ESCALATE_AFTER = 2  # reprovações do Haiku antes de chamar o Opus
STAGES = ("deterministic", "reviewer", "reviewer-senior")


def _load(path=STATE):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data, path=STATE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def spec_rules(spec_path="SPEC.md"):
    """{numero: texto} da seção 'Regras verificáveis pelo revisor' do SPEC.md."""
    text = Path(spec_path).read_text(encoding="utf-8")
    sec = text.split("## Regras verificáveis pelo revisor", 1)[-1]
    return {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"^(\d+)\.\s+(.*)$", sec, re.M)}


def relevant_rule_numbers(paths):
    nums = {1, 3}  # segredos e "revisor só vê diff" valem sempre
    for p in paths:
        if re.fullmatch(r"\.claude/agents/[^/]+\.md", p):
            nums.add(2)
        if p == "TASKS.md":
            nums.add(4)
        if p.endswith(("end-of-task.sh", "tasklog.py", "CLAUDE.md", "SPEC.md")):
            nums.add(5)
    return sorted(nums)


def packet(diff, spec_path="SPEC.md"):
    """Só o diff e as regras relevantes: é isto que o revisor recebe, nunca o projeto."""
    rules = spec_rules(spec_path)
    nums = relevant_rule_numbers(parse_diff(diff).keys())
    lines = [f"{n}. {rules[n]}" for n in nums if n in rules]
    return "REGRAS RELEVANTES:\n" + "\n".join(lines) + "\n\nDIFF:\n" + diff


def next_agent(entry):
    return "reviewer-senior" if entry.get("reviewer", 0) >= ESCALATE_AFTER else "reviewer"


def total_rejections(entry):
    return sum(entry.get(s, 0) for s in STAGES)


def check(task, diff, state_path=STATE, spec_path="SPEC.md"):
    data = _load(state_path)
    entry = data.setdefault(task, {})
    if total_rejections(entry) >= MAX_ATTEMPTS:
        return {"stage": "limite", "verdict": "PARAR",
                "msg": f"{MAX_ATTEMPTS} reprovações nesta tarefa: pare e reporte ao usuário"}
    found = check_diff(diff)
    if found:
        entry["deterministic"] = entry.get("deterministic", 0) + 1
        _save(data, state_path)
        out = {"stage": "deterministic", "verdict": "REPROVADO",
               "violations": [f"{r} {p}:{n}: {m}" for r, p, n, m in found]}
        if total_rejections(entry) >= MAX_ATTEMPTS:
            out["next"] = "PARAR"
        return out
    return {"stage": "reviewer", "verdict": "PENDENTE", "agent": next_agent(entry),
            "packet": packet(diff, spec_path)}


def record(task, stage, verdict, state_path=STATE):
    if stage not in ("reviewer", "reviewer-senior"):
        raise ValueError("stage deve ser reviewer ou reviewer-senior")
    if verdict not in ("APROVADO", "REPROVADO"):
        raise ValueError("verdict deve ser APROVADO ou REPROVADO")
    data = _load(state_path)
    entry = data.setdefault(task, {})
    if verdict == "APROVADO":
        data.pop(task, None)
        _save(data, state_path)
        return {"verdict": "APROVADO", "next": "FIM"}
    entry[stage] = entry.get(stage, 0) + 1
    _save(data, state_path)
    if total_rejections(entry) >= MAX_ATTEMPTS:
        return {"verdict": "REPROVADO", "next": "PARAR"}
    return {"verdict": "REPROVADO", "next": "CORRIGIR", "proximo_revisor": next_agent(entry)}


def main(argv=None):
    p = argparse.ArgumentParser(prog="harness.review_flow")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--task", required=True)
    r = sub.add_parser("record")
    r.add_argument("--task", required=True)
    r.add_argument("--stage", required=True)
    r.add_argument("--verdict", required=True)
    args = p.parse_args(argv)
    try:
        out = check(args.task, sys.stdin.read()) if args.cmd == "check" else record(args.task, args.stage, args.verdict)
    except ValueError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
