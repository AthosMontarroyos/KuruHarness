# TASKS.md — ledger compartilhado

Formato: `- [status] id — descrição (modelo, tentativas, resultado)`. Status: `[ ]` aberto, `[~]` em andamento, `[x]` pronto, `[!]` bloqueado.

## Fase 0 — Base
- [x] 0.1 — `CLAUDE.md`, `SPEC.md`, `TASKS.md` criados
- [!] 0.2 — MCP `kuru-subagents` responde a ping. Bloqueado: `ask_jev` e `ask_deepseek` retornam `404 error code: 1042` (o Worker `kuru-subagents` chama `kuru-ai` via `KURU_URL` por fetch público; Worker→Worker no mesmo account precisa de service binding)
- [ ] 0.3 — Confirmar que o MCP exige token (testar chamada sem `MCP_TOKEN`)
- [ ] 0.4 — Instalar Cursor CLI (`agent`) e fazer login (interativo, na máquina do usuário)

## Fase 1 — Núcleo mínimo
- Não iniciada (depende do critério de pronto da Fase 0)
