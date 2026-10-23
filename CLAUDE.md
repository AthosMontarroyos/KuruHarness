# CLAUDE.md — regras do projeto KuruHarness

Harness de sub-agents do Claude Code. O plano completo e os critérios de pronto de cada fase estão em `SPEC.md`. O estado vivo das tarefas está em `TASKS.md`.

## Regras gerais
- Só avance de fase quando o critério de pronto da fase atual passar. Registre o resultado em `TASKS.md`.
- Máximo de 3 tentativas por tarefa. Na terceira falha, pare e reporte; não tente uma quarta.
- Teto de custo: US$ 5/mês em DeepSeek (saldo real de US$ 5, cuidado) e em Higgsfield. O Worker bloqueia o DeepSeek sozinho ao chegar a US$ 5 estimados (ferramenta `budget_status` mostra o gasto; é estimativa, o saldo real está no painel do DeepSeek). Higgsfield ainda sem bloqueio automático: confira o gasto antes de chamar e avise o usuário ao se aproximar do teto. Jev não tem teto (usuário informa que não cobra); ainda assim, evite chamadas em loop.
- Agentes em paralelo: de 3 a 5.
- O revisor recebe só o diff e as regras relevantes, nunca o projeto inteiro.
- Nunca grave tokens, chaves ou segredos no repositório. `MCP_TOKEN` e afins vivem só como secrets do Worker.
- Commits coesos por intenção, em português, sem push forçado nem reescrita de histórico.

## Fluxo de revisão (Fase 2)
Use `/review <task-id>`. Ordem fixa: 1) `harness/check_rules.py` (grátis, sem modelo); 2) `reviewer` (Haiku) recebendo só o pacote `regras relevantes + diff` gerado por `python3 -m harness.review_flow check`; 3) `reviewer-senior` (Opus) somente depois de 2 reprovações do Haiku na mesma tarefa. Toda reprovação (determinística ou de modelo) conta para o limite de 3 tentativas; na 3ª, parar e reportar. Estado em `.claude/state/reviews.json`. A regra 3 é imposta tecnicamente: os revisores têm `tools: []` e `omitClaudeMd: true` (não leem arquivos nem recebem este CLAUDE.md), e o pacote vai inline no prompt, em partes de até 12 mil caracteres divididas por arquivo.

## Roteamento inicial (proposta; ajustar com os logs da Fase 6)
- Trivial (1 arquivo, baixo risco): Haiku.
- Média: Sonnet.
- Multi-arquivo ou arquitetura: `planner` (Opus). Fable só se o Opus falhar duas vezes.

## Ferramentas externas (MCP `kuru-subagents`)
- `ask_jev`: julgador rápido, sem raciocínio: lê o estado e devolve probabilidades por opção. Serve para acelerar decisões no meio da tarefa (rotear, aprovar/reprovar, urgente ou não), inclusive como porteiro de diffs (Fase 4). Quem raciocina é o Haiku/Claude; use o Jev quando a decisão cabe em opções fechadas. Sempre escreva as regras/critérios no texto da pergunta (sem isso ele aprova quase tudo). Medido na Fase 4: 87,5% de acerto contra 97,5% do Haiku, e a confiança dele NÃO é calibrada (errou com 0,98). O próprio criador do Jev avisa que ele não foi feito para nunca alucinar: trate a saída como indício probabilístico, nunca como prova, e nunca deixe uma ação irreversível depender só dele. Por isso não use o Jev como porteiro de conformidade de diffs; use em roteamento e triagem de baixo risco. Entrada: `state` (string com o diff) e `questions` (objeto; cada pergunta é `{type, instructions, criteria?}` com `type` = `noul` (sim/não, devolve probabilidade), `choice` (criteria = objeto opção→descrição) ou `score` (criteria = lista ordenada)). Uma pergunta que seja string solta dá erro 502/7003. Saída: `{state:"Completed", result:{answers:{...}, usage}}`. Ele só julga, não explica nem pensa; baixa confiança (`confidence` baixa ou probabilidades próximas) escala para o Haiku.
- `ask_deepseek`: reserva para tarefas não sensíveis ou limite estourado (Fase 5). Só devolve texto; o Claude Code aplica o patch.
- `higgsfield_*`: criatividade, fora deste plano.
