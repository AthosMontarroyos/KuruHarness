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
- [x] 1.3 — Teto definido: US$ 5/mês por serviço (DeepSeek, Jev, Higgsfield). Registrado em SPEC/CLAUDE
- [ ] 1.5 — Aplicar o teto de verdade: o Worker `kuru-subagents` precisa contar o gasto por mês (ex.: KV/D1) e recusar chamadas acima de US$ 5; hoje o limite é só regra escrita
- [x] 1.4 — Critério de pronto: tarefa real `harness/tasklog.py` (log por tarefa) planejada por agent Opus, implementada, 6 testes unittest verdes e hook `end-of-task.sh` verde (exit 0). Obs.: planner/reviewer/quick-decider ainda não carregados nesta sessão; usei agents comuns equivalentes

## Fase 6 — Medição (antecipada como tarefa real da Fase 1)
- [x] 6.1 — `harness/tasklog.py` + `tests/test_tasklog.py` (JSONL em `.claude/state/tasks.jsonl`, resumo por modelo)
- [ ] 6.2 — Integrar ao hook: gravar tentativas/resultado automaticamente (hoje o registro é manual; tokens não são acessíveis ao hook)

## Fase 2 — Verificador de conformidade
- [x] 2.1 — Critério de pronto: `reviewer` (Haiku) reprovou de propósito um diff com token literal e sem `model` (violando regras 1 e 2 do SPEC) e aprovou o diff corrigido

## Fase 4 — Jev como porteiro
- [x] 4.0 — `ask_jev` funcional (formato `state` + `questions` tipadas). Teste único: diff com token literal → `veredito=reprovar` (0.97), `segredo=0.96`; `sem_model` só 0.74 (pergunta de ausência é mais fraca)
- [ ] 4.1 — Montar 50–100 diffs rotulados e comparar Jev × Haiku; entra só se a acurácia nos casos de alta confiança for aceitável
