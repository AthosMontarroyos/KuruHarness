# CLAUDE.md — regras do projeto KuruHarness

Harness de sub-agents do Claude Code. O plano completo e os critérios de pronto de cada fase estão em `SPEC.md`. O estado vivo das tarefas está em `TASKS.md`.

## Regras gerais
- Só avance de fase quando o critério de pronto da fase atual passar. Registre o resultado em `TASKS.md`.
- Máximo de 3 tentativas por tarefa. Na terceira falha, pare e reporte; não tente uma quarta.
- Teto de custo: US$ 5/mês em DeepSeek (saldo real de US$ 5, cuidado) e em Higgsfield. Antes de chamar, confira o gasto do mês; ao atingir o teto, não chame e avise o usuário. Jev não tem teto (usuário informa que não cobra); ainda assim, evite chamadas em loop.
- Agentes em paralelo: de 3 a 5.
- O revisor recebe só o diff e as regras relevantes, nunca o projeto inteiro.
- Nunca grave tokens, chaves ou segredos no repositório. `MCP_TOKEN` e afins vivem só como secrets do Worker.
- Commits coesos por intenção, em português, sem push forçado nem reescrita de histórico.

## Roteamento inicial (proposta; ajustar com os logs da Fase 6)
- Trivial (1 arquivo, baixo risco): Haiku.
- Média: Sonnet.
- Multi-arquivo ou arquitetura: `planner` (Opus). Fable só se o Opus falhar duas vezes.

## Ferramentas externas (MCP `kuru-subagents`)
- `ask_jev`: julgador rápido, sem raciocínio: lê o estado e devolve probabilidades por opção. Serve para acelerar decisões no meio da tarefa (rotear, aprovar/reprovar, urgente ou não), inclusive como porteiro de diffs (Fase 4). Quem raciocina é o Haiku/Claude; use o Jev quando a decisão cabe em opções fechadas. Sempre escreva as regras/critérios no texto da pergunta (sem isso ele aprova quase tudo). Medido na Fase 4: 87,5% de acerto contra 97,5% do Haiku, e a confiança dele NÃO é calibrada (errou com 0,98). O próprio criador do Jev avisa que ele não foi feito para nunca alucinar: trate a saída como indício probabilístico, nunca como prova, e nunca deixe uma ação irreversível depender só dele. Por isso não use o Jev como porteiro de conformidade de diffs; use em roteamento e triagem de baixo risco. Entrada: `state` (string com o diff) e `questions` (objeto; cada pergunta é `{type, instructions, criteria?}` com `type` = `noul` (sim/não, devolve probabilidade), `choice` (criteria = objeto opção→descrição) ou `score` (criteria = lista ordenada)). Uma pergunta que seja string solta dá erro 502/7003. Saída: `{state:"Completed", result:{answers:{...}, usage}}`. Ele só julga, não explica nem pensa; baixa confiança (`confidence` baixa ou probabilidades próximas) escala para o Haiku.
- `ask_deepseek`: reserva para tarefas não sensíveis ou limite estourado (Fase 5). Só devolve texto; o Claude Code aplica o patch.
- `higgsfield_*`: criatividade, fora deste plano.
