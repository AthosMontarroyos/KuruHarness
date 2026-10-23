# TASKS.md — ledger compartilhado

Formato: `- [status] id — descrição (modelo, tentativas, resultado)`. Status: `[ ]` aberto, `[~]` em andamento, `[x]` pronto, `[!]` bloqueado.

## Fase 0 — Base
- [x] 0.1 — `CLAUDE.md`, `SPEC.md`, `TASKS.md` criados
- [x] 0.2 — MCP lista as ferramentas e `ask_deepseek` respondeu `pong`. O erro 1042 inicial (fetch público Worker→Worker) foi corrigido por fora. `ask_jev` segue sem créditos (esperado; só entra na Fase 4)
- [x] 0.3 — MCP exige token: `POST /mcp` sem credencial retorna 401
- [ ] 0.4 — Instalar Cursor CLI (`agent`) e fazer login. Adiado: só no PC do usuário, que não está disponível agora; só é necessário na Fase 3

## Fase 1 — Núcleo mínimo
- [x] 1.1 — Subagents `planner` (opus), `reviewer` (haiku), `quick-decider` (haiku, effort low) em `.claude/agents/`
- [x] 1.2 — Hook Stop `scripts/end-of-task.sh` (testes, linter, typecheck; 3 tentativas). Testado: sem tooling passa; com teste falhando bloqueia 2x e libera na 3ª
- [x] 1.3 — Teto definido: US$ 5/mês em DeepSeek e Higgsfield; Jev sem cobrança (usuário recarregou US$ 10 no AI Gateway). Registrado em SPEC/CLAUDE
- [x] 1.5 — Teto mensal do DeepSeek aplicado no Worker `kuru-subagents`: D1 `kuru-budget-db` (tabela `spend`, incremento atômico), bloqueio ao chegar a US$ 5 estimados, ferramenta `budget_status`. Testado: chamada normal soma 22 µUSD; com o contador forçado a US$ 5 a chamada é recusada; contador restaurado. Rollback: versão anterior `cfa57da4-3bf1-4765-b241-a42d6063d1f6`. Limitações: o gasto é ESTIMADO (chars/3 tokens, US$ 0,30/M entrada e US$ 1,20/M saída, conservador), não o saldo real do DeepSeek; o contador começou do zero em 2026-10 (não conta gasto anterior). Higgsfield e Jev sem teto no Worker (preço do Higgsfield não conhecido). Primeira tentativa com KV foi descartada: leitura em cache e sem incremento atômico subestimava o gasto
- [x] 1.4 — Critério de pronto: tarefa real `harness/tasklog.py` (log por tarefa) planejada por agent Opus, implementada, 6 testes unittest verdes e hook `end-of-task.sh` verde (exit 0). Obs.: planner/reviewer/quick-decider ainda não carregados nesta sessão; usei agents comuns equivalentes

## Fase 6 — Medição (antecipada como tarefa real da Fase 1)
- [x] 6.1 — `harness/tasklog.py` + `tests/test_tasklog.py` (JSONL em `.claude/state/tasks.jsonl`, resumo por modelo)
- [ ] 6.2 — Integrar ao hook: gravar tentativas/resultado automaticamente (hoje o registro é manual; tokens não são acessíveis ao hook)

## Fase 2 — Verificador de conformidade
- [x] 2.1 — Critério de pronto: `reviewer` (Haiku) reprovou de propósito um diff com token literal e sem `model` (violando regras 1 e 2 do SPEC) e aprovou o diff corrigido

## Fase 4 — Jev como porteiro
- [x] 4.0 — `ask_jev` funcional (formato `state` + `questions` tipadas). Teste único: diff com token literal → `veredito=reprovar` (0.97), `segredo=0.96`; `sem_model` só 0.74 (pergunta de ausência é mais fraca)
- [~] 4.1 — Casos rotulados e comparação Jev × Haiku (`harness/eval/`, `python3 harness/eval/score.py`). Rodados 40 casos (R1, R2, R4, R5); os 10 mistos têm rótulo e resposta do Haiku, mas o Jev não foi rodado neles. Resultado: Jev 35/40 (87,5%), Haiku 39/40 (97,5%). Jev em alta confiança (>=0,8): 29/34 (85%); errou com confiança 0,98 em R2 (`model:` vazio, `model` no corpo, typo `models:`) e em R4. **Critério de entrada como porteiro de diffs NÃO atendido.** Limitações: rótulos sintéticos (gerados por LLM, sem conferência humana), r1 usou pergunta sem as regras no texto, r4-05 tem rótulo discutível (ambos erraram).
- [ ] 4.2 — Decisão: usar Jev só em decisões semânticas de baixo risco no meio da tarefa; regras estruturais (R1 regex, R2 parse do frontmatter) ficam em checagem determinística + Haiku. Pendente: validar com o usuário e rodar o Jev nos 10 mistos
