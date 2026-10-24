#!/usr/bin/env bash
# Instala o kit KuruHarness (subagents, comandos, hook e scripts) no projeto atual, SEM clonar o repo:
# baixa só o tarball do GitHub, copia o kit e descarta o resto. Rodar de novo atualiza o kit.
#   cd meu-projeto && curl -fsSL https://raw.githubusercontent.com/AthosMontarroyos/KuruHarness/main/install.sh | bash
# Variáveis: KURU_REF (padrão main), KURU_REPO (padrão AthosMontarroyos/KuruHarness),
#            KURU_SRC_DIR (usa uma pasta local em vez de baixar; serve para testes)
# Não sobrescreve: settings.json, CLAUDE.md, SPEC.md e .gitignore do projeto são MESCLADOS (blocos
# marcados com kuru-harness). Agents e comandos com os mesmos nomes do kit são atualizados.
set -euo pipefail
REPO="${KURU_REPO:-AthosMontarroyos/KuruHarness}"
REF="${KURU_REF:-main}"
DEST="$PWD"
command -v python3 >/dev/null || { echo "python3 é necessário" >&2; exit 1; }

# não pisa numa pasta harness/ que seja de outra coisa
if [ -d "$DEST/harness" ] && [ ! -f "$DEST/harness/route.py" ]; then
  echo "já existe uma pasta harness/ que não é do kit; nada foi alterado" >&2
  exit 1
fi

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
if [ -n "${KURU_SRC_DIR:-}" ]; then
  src="$KURU_SRC_DIR"
else
  curl -fsSL --max-time 90 "https://codeload.github.com/$REPO/tar.gz/$REF" | tar -xz -C "$tmp" --strip-components=1
  src="$tmp"
fi
[ -f "$src/harness/route.py" ] && [ -f "$src/.claude/settings.json" ] || { echo "kit não encontrado em $REPO@$REF" >&2; exit 1; }

mkdir -p "$DEST/.claude/agents" "$DEST/.claude/commands" "$DEST/harness" "$DEST/scripts"
cp "$src"/.claude/agents/*.md "$DEST/.claude/agents/"
cp "$src"/.claude/commands/*.md "$DEST/.claude/commands/"
cp "$src"/harness/*.py "$DEST/harness/"            # sem harness/eval nem tests: são do repo do kit
cp "$src/scripts/end-of-task.sh" "$src/scripts/cursor-task.sh" "$DEST/scripts/"
chmod +x "$DEST/scripts/end-of-task.sh" "$DEST/scripts/cursor-task.sh"

python3 - "$src" "$DEST" <<'PY'
import json, os, re, sys

src, dest = sys.argv[1], sys.argv[2]
START, END = "<!-- kuru-harness:start -->", "<!-- kuru-harness:end -->"


def put_block(path, body, header=""):
    """Insere ou substitui o bloco marcado do kit, sem mexer no resto do arquivo."""
    cur = open(path, encoding="utf-8").read() if os.path.exists(path) else header
    block = f"{START}\n{body.rstrip()}\n{END}\n"
    pat = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
    if pat.search(cur):
        cur = pat.sub(lambda m: block, cur)
    else:
        cur = cur.rstrip("\n") + ("\n\n" if cur.strip() else "") + block
    open(path, "w", encoding="utf-8").write(cur)


# settings.json: une hooks e permissões sem remover nada do projeto
kit = json.load(open(f"{src}/.claude/settings.json"))
path = f"{dest}/.claude/settings.json"
cur = json.load(open(path)) if os.path.exists(path) else {}
for event, groups in kit.get("hooks", {}).items():
    have = cur.setdefault("hooks", {}).setdefault(event, [])
    seen = {h.get("command") for g in have for h in g.get("hooks", [])}
    for g in groups:
        if not any(h.get("command") in seen for h in g.get("hooks", [])):
            have.append(g)
allow = cur.setdefault("permissions", {}).setdefault("allow", [])
allow += [a for a in kit.get("permissions", {}).get("allow", []) if a not in allow]
json.dump(cur, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(path, "a").write("\n")

# CLAUDE.md: as regras do kit (a partir de "## Regras gerais"; o "Escopo" é do repo do kit)
text = open(f"{src}/CLAUDE.md", encoding="utf-8").read()
put_block(f"{dest}/CLAUDE.md", text[text.index("## Regras gerais"):], "# CLAUDE.md\n")

# SPEC.md: o fluxo de revisão lê as regras numéricas daqui
spec = open(f"{src}/SPEC.md", encoding="utf-8").read()
put_block(f"{dest}/SPEC.md", spec[spec.index("## Regras verificáveis pelo revisor"):], "# SPEC.md\n")

# .gitignore
gi = f"{dest}/.gitignore"
lines = open(gi).read().splitlines() if os.path.exists(gi) else []
lines += [l for l in (".claude/state/", ".claude/worktrees/", "__pycache__/", "*.pyc") if l not in lines]
open(gi, "w").write("\n".join(lines) + "\n")
PY

echo "KuruHarness instalado em $DEST ($REPO@$REF)."
echo "Reinicie a sessão do Claude Code para carregar os subagents e comandos (/task, /review, /fallback)."
echo "Confie no projeto uma vez: o Claude Code ignora permissions.allow de workspace não confiável."
