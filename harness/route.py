"""Roteamento de tarefas (regra inicial do CLAUDE.md), determinístico e testável.

    bash bin/kuru route "renomear variável em utils.py" --files harness/utils.py

Delegar custa tokens (prompt do agente + briefing + resposta), então só vale quando poupa o contexto
principal ou muda a qualidade. Por isso:
  trivial  -> o próprio Claude faz, SEM agente
  media    -> o próprio Claude faz, SEM agente (delegar só se for explorar muito: ver `delegar_se`)
  complexa -> planner (Opus, contexto isolado) e depois a implementação
  longa    -> planner e depois vários implementer-sonnet em paralelo, cada um com um grupo independente de arquivos.
Risco alto sobe um tier (nunca abaixo de `media`). Quando o sinal é fraco, devolve
`incerta=True`: aí vale perguntar ao quick-decider (Haiku) ou ao Jev. O Jev só pode SUBIR o tier,
nunca baixar (a confiança dele não é calibrada, ver CLAUDE.md).
"""
import argparse
import json
import re
import sys

TIERS = ("trivial", "media", "complexa", "longa")
AGENTS = {
    "trivial": [],
    "media": [],
    "complexa": ["planner", "implementer-sonnet"],
    "longa": ["planner", "implementer-sonnet"],  # o Sonnet em paralelo (3 a 5), um grupo de arquivos cada
}
DELEGATE_IF = "a tarefa exigir ler ou explorar mais de 6 arquivos, ou logs/diffs grandes que poluiriam o contexto: use implementer-sonnet com briefing"
PARALELO_LONGA = "depois do plano, divida os arquivos em grupos independentes e rode de 3 a 5 implementer-sonnet em paralelo, cada um com o seu briefing"

TRIVIAL_KW = re.compile(r"(?i)\b(typo|erro de digita[cç][aã]o|renomear|comentario|coment[aá]rio|texto|readme|docstring|formata[cç][aã]o|lint)\b")
COMPLEX_KW = re.compile(r"(?i)\b(arquitetura|projet(?:e|ar|ando)\b|design|decis[aã]o de design|refator\w*|migra\w*|redesenh\w*|multi-?arquivo|m[oó]dulo novo|api p[uú]blica|esquema|schema)\b")
LONG_KW = re.compile(r"(?i)\b(longa|demorada|reescrever|reimplementar|implementar do zero|feature grande)\b")
# "9 módulos", "12 arquivos": quando o Claude não passa --files, a contagem escrita na descrição vale
COUNT_RE = re.compile(r"(?i)\b(\d+)\s+(?:arquivos?|m[oó]dulos?|componentes?|servi[cç]os?|telas?|classes?|endpoints?|files?)\b")
RISK_KW = re.compile(r"(?i)\b(seguran[cç]a|auth\w*|pagamento\w*|produ[cç][aã]o|deploy\w*|segredo\w*|token\w*|credencia\w+|migra[cç][aã]o de dados|apag\w+|delet\w+)")


def classify(description, files=None):
    desc = description or ""
    n = len(files) if files else None
    m = COUNT_RE.search(desc)
    if m:  # a contagem escrita não pode ser reduzida por uma lista --files incompleta: vale a maior
        n = max(n or 0, int(m.group(1)))
    reasons, score = [], None

    if n is not None:
        score = 0 if n <= 1 else 1 if n <= 3 else 2 if n <= 7 else 3
        reasons.append(f"{n} arquivo(s)")
    if LONG_KW.search(desc) or (n is not None and n >= 8):
        score = 3
        reasons.append("tarefa longa")
    elif COMPLEX_KW.search(desc):
        score = max(score or 0, 2)
        reasons.append("palavras de arquitetura/refatoração")
    elif TRIVIAL_KW.search(desc) and (score is None or score <= 1):
        score = 0 if score is None or score == 0 else 1
        reasons.append("palavras de mudança trivial")

    incerta = score is None
    if incerta:
        score = 1  # sem sinais: assume média, mas marca como incerta
        reasons.append("sem sinais claros de tamanho: conte os arquivos que a mudança toca e rode de novo com --files")

    risk = bool(RISK_KW.search(desc))
    if risk:
        score = min(3, max(score + 1, 1))
        reasons.append("risco alto: sobe um tier")

    tier = TIERS[score]
    out = {"tier": tier, "acao": "agente" if AGENTS[tier] else "direto", "agents": AGENTS[tier],
           "incerta": incerta, "risco": risk, "motivos": reasons}
    if tier == "media":
        out["delegar_se"] = DELEGATE_IF
    if tier == "longa":
        out["cadeia"] = AGENTS[tier]
        out["paralelo"] = PARALELO_LONGA
    return out


def jev_questions(description):
    """Pergunta para o ask_jev (escreve o critério no texto, como manda o CLAUDE.md)."""
    return {
        "tier": {
            "type": "choice",
            "instructions": "Qual o tamanho desta tarefa de código?",
            "criteria": {
                "trivial": "1 arquivo, mudança pequena e de baixo risco (typo, renomear, texto)",
                "media": "2 a 3 arquivos ou lógica nova pequena, sem decisão de arquitetura",
                "complexa": "4 ou mais arquivos, ou decisão de arquitetura/refatoração",
            },
        }
    }


def apply_jev(result, jev_choice, min_prob=0.8):
    """Combina o veredito heurístico com a resposta do Jev: o Jev só SOBE o tier."""
    if jev_choice.get("choice") not in TIERS:
        return result
    probs = jev_choice.get("probabilities", {})
    if probs.get(jev_choice["choice"], 0) < min_prob:
        return result
    if TIERS.index(jev_choice["choice"]) > TIERS.index(result["tier"]):
        tier = jev_choice["choice"]
        result = dict(result, tier=tier, acao="agente" if AGENTS[tier] else "direto", agents=AGENTS[tier],
                      motivos=result["motivos"] + [f"Jev sugeriu {tier}"])
        result.pop("delegar_se", None)
        if tier == "media":
            result["delegar_se"] = DELEGATE_IF
    return result


def main(argv=None):
    p = argparse.ArgumentParser(prog="harness.route")
    p.add_argument("description")
    p.add_argument("--files", nargs="*", default=None)
    p.add_argument("--jev-questions", action="store_true", help="imprime só as perguntas para o ask_jev")
    args = p.parse_args(argv)
    if args.jev_questions:
        print(json.dumps(jev_questions(args.description), ensure_ascii=False))
        return 0
    print(json.dumps(classify(args.description, args.files), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
