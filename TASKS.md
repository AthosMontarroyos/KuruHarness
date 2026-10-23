# TASKS.md — ledger compartilhado

Formato: `- [status] id — descrição (modelo, tentativas, resultado)`. Status: `[ ]` aberto, `[~]` em andamento, `[x]` pronto, `[!]` bloqueado.

## Fase 0 — Base
- [x] 0.1 — `CLAUDE.md`, `SPEC.md`, `TASKS.md` criados
- [x] 0.2 — MCP lista as ferramentas e `ask_deepseek` respondeu `pong`. O erro 1042 inicial (fetch público Worker→Worker) foi corrigido por fora. `ask_jev` segue sem créditos (esperado; só entra na Fase 4)
- [x] 0.3 — MCP exige token: `POST /mcp` sem credencial retorna 401
- [ ] 0.4 — Instalar Cursor CLI (`agent`) e fazer login (interativo, na máquina do usuário)

## Fase 1 — Núcleo mínimo
- [x] 1.1 — Subagents `planner` (opus), `reviewer` (haiku), `quick-decider` (haiku, effort low) em `.claude/agents/`
- [x] 1.2 — Hook Stop `scripts/end-of-task.sh` (testes, linter, typecheck; 3 tentativas). Testado: sem tooling passa; com teste falhando bloqueia 2x e libera na 3ª
- [ ] 1.3 — Teto de custo: valor pendente do usuário (o harness não mede custo sozinho)
- [ ] 1.4 — Critério de pronto: uma tarefa real de plano a teste verde (este repo ainda não tem código/testes)
