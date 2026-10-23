#!/usr/bin/env bash
# Hook Stop: roda testes, linter e typecheck do projeto, se configurados.
# Reprova (exit 2) devolvendo o erro ao Claude. Máximo de 3 tentativas por tarefa.
set -u
cd "${CLAUDE_PROJECT_DIR:-.}"
STATE=.claude/state; mkdir -p "$STATE"
MAX=3
n=$(cat "$STATE/attempts" 2>/dev/null || echo 0)

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
[ -f tests/__init__.py ] && command -v python3 >/dev/null && run unittest python3 -m unittest discover -s tests -t . -q

if [ $fail -eq 0 ]; then
  echo 0 > "$STATE/attempts"; exit 0
fi

n=$((n+1)); echo $n > "$STATE/attempts"
if [ $n -ge $MAX ]; then
  echo "Limite de $MAX tentativas atingido. Pare e reporte ao usuário o que falhou:$out" >&2
  echo 0 > "$STATE/attempts"; exit 0   # libera a parada para o humano decidir
fi
echo "Verificação falhou (tentativa $n/$MAX). Corrija:$out" >&2
exit 2
