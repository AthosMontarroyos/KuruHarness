#!/usr/bin/env bash
# Fase 3: roda UMA tarefa no Cursor CLI (`agent`) num git worktree isolado e devolve o diff para o
# Claude Code revisar (skill delegar, passo 5) e aplicar. Sessão nova a cada tarefa (nunca --resume/--continue,
# por causa do bug do --resume). No máximo 3 em paralelo.
#   scripts/cursor-task.sh <task-id> <arquivo-com-o-prompt>
#   scripts/cursor-task.sh --clean <task-id>      # remove worktree e branch depois de aplicar/descartar
# Variáveis: CURSOR_MODEL (padrão grok-4.7-high-fast), CURSOR_MAX_PARALLEL (3),
#            CURSOR_SANDBOX (enabled; use disabled se o agent precisar de rede/comandos fora do worktree)
set -euo pipefail
MODEL="${CURSOR_MODEL:-grok-4.7-high-fast}"
MAX_PARALLEL="${CURSOR_MAX_PARALLEL:-3}"
SANDBOX="${CURSOR_SANDBOX:-enabled}"

if [ "${1:-}" = "--clean" ]; then
  id="${2:?uso: --clean <task-id>}"
  cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
  git worktree remove --force ".claude/worktrees/$id" 2>/dev/null || true
  git branch -D "cursor/$id" 2>/dev/null || true
  exit 0
fi

[ $# -ge 2 ] || { echo "uso: cursor-task.sh <task-id> <arquivo-prompt>" >&2; exit 2; }
id="$1"
prompt_file="$(realpath "$2")"
[[ "$id" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "task-id inválido (use letras, números, . _ -)" >&2; exit 2; }
[ -s "$prompt_file" ] || { echo "arquivo de prompt vazio ou inexistente: $prompt_file" >&2; exit 2; }
# O Cursor NÃO lê o CLAUDE.md: o prompt precisa carregar as regras do projeto por extenso (use `kuru brief`).
grep -qF "# Regras do projeto (obrigatórias)" "$prompt_file" || { echo "o prompt não tem as regras do projeto: gere o briefing com 'bash bin/kuru brief --task ... --out <arquivo>'" >&2; exit 2; }
command -v agent >/dev/null || { echo "Cursor CLI (agent) não encontrado no PATH" >&2; exit 127; }

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
STATE=.claude/state/cursor; mkdir -p "$STATE/slots"

slot=""
for i in $(seq 1 "$MAX_PARALLEL"); do
  d="$STATE/slots/$i"
  if ! mkdir "$d" 2>/dev/null; then
    p="$(cat "$d/pid" 2>/dev/null || true)"
    if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then continue; fi   # vaga ocupada por processo vivo
    rm -rf "$d"; mkdir "$d" 2>/dev/null || continue                 # processo morto: reaproveita
  fi
  echo $$ > "$d/pid"; slot="$d"; break
done
[ -n "$slot" ] || { echo "sem vaga: já há $MAX_PARALLEL tarefas do Cursor em paralelo" >&2; exit 75; }
trap 'rm -rf "$slot"' EXIT

wt=".claude/worktrees/$id"
[ ! -e "$wt" ] || { echo "worktree já existe: rode --clean $id antes" >&2; exit 2; }
git worktree add -q -b "cursor/$id" "$wt" HEAD

log="$STATE/$id.log"; diff="$STATE/$id.diff"
set +e
( cd "$wt" && agent -p --trust --force --sandbox "$SANDBOX" --model "$MODEL" \
    --output-format text "$(cat "$prompt_file")" ) > "$log" 2>&1
rc=$?
set -e

git -C "$wt" add -A
git -C "$wt" diff --cached > "$diff"
files=$(git -C "$wt" diff --cached --name-only | wc -l | tr -d ' ')
echo "agent saiu com $rc | modelo $MODEL | $files arquivo(s) alterado(s)"
echo "diff: $diff | log: $log | worktree: $wt (limpe com: scripts/cursor-task.sh --clean $id)"
if [ "$rc" -ne 0 ]; then
  # Falha de infraestrutura do Cursor: o Claude desce para o próximo codificador (skill delegar, passo 3) (DeepSeek, depois Sonnet).
  # O texto exato do erro de "sem saldo" não foi observado: o padrão abaixo é um palpite só para o motivo.
  if grep -Eiq "usage limit|rate limit|out of (credits|requests)|quota|credit|billing|upgrade|spend limit|payment|exceeded|402" "$log"; then
    echo "cursor_indisponivel: provável falta de saldo/limite (veja $log)" >&2
    exit 76
  fi
  exit "$rc"
fi
