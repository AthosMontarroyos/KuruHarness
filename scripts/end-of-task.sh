#!/usr/bin/env bash
# Hook Stop: roda testes, linter e typecheck do projeto, se configurados.
# Reprova (exit 2) devolvendo o erro ao Claude. Máximo de 3 tentativas por tarefa.
set -u
[ "${1:-}" = "--diff" ] && export KURU_RULES_MODE=diff   # instalação global: sem depender de variável de ambiente no comando do hook
# O kit é achado pela localização deste script (funciona em qualquer pasta do projeto e no Windows).
KURU="$(cd "$(dirname "${BASH_SOURCE[0]}")/../bin" && pwd)/kuru"
cd "${CLAUDE_PROJECT_DIR:-.}"
# O Claude Code passa um JSON (session_id, transcript_path) no stdin; sem stdin, segue sem ele.
HOOK_INPUT=""; if [ ! -t 0 ]; then HOOK_INPUT=$(timeout 2 cat 2>/dev/null || true); fi; export HOOK_INPUT
MAIN="$PWD"; STATE="$MAIN/.claude/state"; mkdir -p "$STATE"
# Tarefa longa em worktree isolado (kuru worktree create): confere o que o Claude fez lá, não a edição do usuário na IDE.
WORK="$MAIN"; BASE=""
if [ -f .kuru/active-worktree ]; then
  wt=$(sed -n 1p .kuru/active-worktree | tr -d '\r'); BASE=$(sed -n 2p .kuru/active-worktree | tr -d '\r')
  [ -d "$wt" ] && WORK="$wt" || BASE=""
fi
cd "$WORK"
MAX=3
n=$(cat "$STATE/attempts" 2>/dev/null || echo 0)

dirty=$(git status --porcelain -- . ':!.claude/state' 2>/dev/null | head -n 1)
# no worktree o trabalho costuma estar commitado: commits além da base também contam como trabalho
[ -z "$dirty" ] && [ -n "$BASE" ] && [ "$(git rev-list --count "$BASE"..HEAD 2>/dev/null || echo 0)" -gt 0 ] && dirty=commits
# turno sem mudança (pergunta, conversa) e sem falha pendente: nada a conferir, não gasta a suíte
[ -z "$dirty" ] && [ "$n" -eq 0 ] && exit 0

fail=0; out=""
run() { # nome, comando...
  local name=$1; shift
  local o; o=$("$@" 2>&1) || { fail=1; out+=$'\n'"== $name falhou =="$'\n'"$(echo "$o" | tail -n 30)"; }
}

if [ -f package.json ]; then
  has() { node -e "process.exit((require('./package.json').scripts||{})['$1']?0:1)"; }
  has test      && run test      npm test --silent
  has lint      && run lint      npm run lint --silent
  has typecheck && run typecheck npm run typecheck --silent
fi
[ -f pyproject.toml ] && command -v pytest >/dev/null && run pytest pytest -q
[ -f pyproject.toml ] && command -v ruff   >/dev/null && run ruff ruff check .
[ -f pyproject.toml ] && command -v mypy   >/dev/null && run mypy mypy .
[ -f tests/__init__.py ] && run unittest bash "$KURU" unittest
# KURU_RULES_MODE=diff (instalação global): em projeto alheio, confere só o que mudou, não o repo inteiro
if [ "${KURU_RULES_MODE:-tree}" = diff ]; then
  run regras bash -c 'git diff HEAD 2>/dev/null | bash "$0" check-rules --diff' "$KURU"
else
  run regras bash "$KURU" check-rules
fi

log_task() { # resultado, tentativas -> .claude/state/tasks.jsonl (nunca derruba o hook)
  (cd "$MAIN" && bash "$KURU" hooklog --result "$1" --attempts "$2" 2>/dev/null) || true
}

if [ $fail -eq 0 ]; then
  # só registra quando houve trabalho (mudanças pendentes ou falhas anteriores)
  if [ -n "$dirty" ] || [ "$n" -gt 0 ]; then log_task ok $((n+1)); fi
  echo 0 > "$STATE/attempts"; exit 0
fi

n=$((n+1)); echo $n > "$STATE/attempts"
if [ $n -ge $MAX ]; then
  log_task fail "$MAX"
  echo "Limite de $MAX tentativas atingido. Pare e reporte ao usuário o que falhou:$out" >&2
  echo 0 > "$STATE/attempts"; exit 0   # libera a parada para o humano decidir
fi
echo "Verificação falhou (tentativa $n/$MAX). Corrija:$out" >&2
exit 2
