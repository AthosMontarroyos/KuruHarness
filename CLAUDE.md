# CLAUDE.md — regras do projeto KuruHarness

Harness de sub-agents do Claude Code. O plano completo e os critérios de pronto de cada fase estão em `SPEC.md`. O estado vivo das tarefas está em `TASKS.md`.

## Regras gerais
- Só avance de fase quando o critério de pronto da fase atual passar. Registre o resultado em `TASKS.md`.
- Máximo de 3 tentativas por tarefa. Na terceira falha, pare e reporte; não tente uma quarta.
- Teto de custo: US$ 5/mês em cada serviço externo (DeepSeek, Jev, Higgsfield). Antes de chamar um deles, confira o gasto do mês; ao atingir o teto, não chame e avise o usuário.
- Agentes em paralelo: de 3 a 5.
- O revisor recebe só o diff e as regras relevantes, nunca o projeto inteiro.
- Nunca grave tokens, chaves ou segredos no repositório. `MCP_TOKEN` e afins vivem só como secrets do Worker.
- Commits coesos por intenção, em português, sem push forçado nem reescrita de histórico.

## Roteamento inicial (proposta; ajustar com os logs da Fase 6)
- Trivial (1 arquivo, baixo risco): Haiku.
- Média: Sonnet.
- Multi-arquivo ou arquitetura: `planner` (Opus). Fable só se o Opus falhar duas vezes.

## Ferramentas externas (MCP `kuru-subagents`)
- `ask_jev`: porteiro de diffs (Fase 4). Entrada: `state` (string com o diff) e `questions` (objeto; cada pergunta é `{type, instructions, criteria?}` com `type` = `noul` (sim/não, devolve probabilidade), `choice` (criteria = objeto opção→descrição) ou `score` (criteria = lista ordenada)). Uma pergunta que seja string solta dá erro 502/7003. Saída: `{state:"Completed", result:{answers:{...}, usage}}`. Ele só classifica, não explica.
- `ask_deepseek`: reserva para tarefas não sensíveis ou limite estourado (Fase 5). Só devolve texto; o Claude Code aplica o patch.
- `higgsfield_*`: criatividade, fora deste plano.
