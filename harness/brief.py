"""Briefing autocontido para qualquer agente que começa SEM contexto (subagents, DeepSeek).

    bash bin/kuru brief --task "..." --files a.py b.py --criteria "..." --tests "kuru unittest" --out .kuru/t1.prompt

Subagents isolados não veem a conversa nem o CLAUDE.md do projeto: tudo o que eles precisam saber vai
escrito no briefing. As regras do projeto vêm da seção "## Regras para quem codifica" do CLAUDE.md
(uma fonte só da verdade). O marcador RULES_MARKER identifica o bloco de regras dentro do briefing.
"""
import argparse
import re
import sys
from pathlib import Path

RULES_HEADER = "## Regras para quem codifica"
RULES_MARKER = "# Regras do projeto (obrigatórias)"


class BriefError(Exception):
    pass


def project_rules(claude_md="CLAUDE.md"):
    """Texto da seção de regras para quem codifica (do CLAUDE.md do projeto; senão o do kit)."""
    kit = Path(__file__).resolve().parent.parent / "CLAUDE.md"
    for cand in (Path(claude_md), kit):
        if cand.exists():
            text = cand.read_text(encoding="utf-8")
            m = re.search(re.escape(RULES_HEADER) + r"[^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
            if m and m.group(1).strip():
                return m.group(1).strip()
    raise BriefError(f'seção "{RULES_HEADER}" não encontrada no CLAUDE.md')


def build(task, files=(), criteria="", tests="", rules=None):
    if not task or not task.strip():
        raise BriefError("a tarefa não pode ser vazia")
    rules = project_rules() if rules is None else rules
    files_txt = "\n".join(f"- {f}" for f in files) if files else "- (nenhum arquivo indicado: descubra quais precisa ler, e leia só o necessário)"
    tests_txt = f"`{tests}`" if tests else "os testes e linters que o projeto tiver (veja package.json, pyproject.toml ou a pasta tests/)"
    return f"""# Tarefa
{task.strip()}

# Arquivos
{files_txt}
Leia antes de editar. Não altere nenhum outro arquivo além do que a tarefa exige.

{RULES_MARKER}
{rules}

# Como trabalhar (siga na ordem)
1. Leia os arquivos acima e entenda o que existe antes de mudar.
2. Faça a menor mudança que cumpre a tarefa. Não refatore, não renomeie e não "melhore" o que não foi pedido.
3. Rode {tests_txt} e corrija até passar. No máximo 3 tentativas: na terceira falha, pare e descreva o que falhou.
4. NÃO faça commit, NÃO faça push, NÃO instale dependências globais e NÃO mexa em arquivos de configuração do projeto.
5. Nunca escreva chaves, tokens ou senhas em nenhum arquivo.

# Critério de pronto
{criteria.strip() if criteria.strip() else "A tarefa está feita, os testes passam e nenhum outro arquivo foi alterado."}

# Entrega
Deixe as mudanças no diretório de trabalho, sem commit. Termine com: arquivos alterados, comandos que rodou e o resultado deles. Seja breve.
"""


def main(argv=None):
    p = argparse.ArgumentParser(prog="kuru brief", description="Monta um briefing autocontido para um agente sem contexto.")
    p.add_argument("--task")
    p.add_argument("--files", nargs="*", default=[])
    p.add_argument("--criteria", default="")
    p.add_argument("--tests", default="", help="comando de teste do projeto (padrão: o agente descobre)")
    p.add_argument("--out", help="grava o briefing neste arquivo em vez de imprimir")
    p.add_argument("--print-rules", action="store_true", help="imprime só as regras para quem codifica")
    a = p.parse_args(argv)
    try:
        if a.print_rules:
            print(project_rules())
            return 0
        text = build(a.task, a.files, a.criteria, a.tests)
    except BriefError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8", newline="\n")
        print(a.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
