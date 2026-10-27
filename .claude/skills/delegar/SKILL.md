---
name: delegar
description: Procedimento exato para delegar uma tarefa NÃO trivial a subagents (roteamento, briefing autocontido, cadeia de codificadores, revisão em 3 estágios). Use antes de delegar. Não use para tarefa trivial: nesse caso faça você mesmo, sem agente.
---
Só o Claude Code executa este procedimento (usa subagents e o `kuru`). Se você é o agente da IDE (Cursor), não o siga: edite direto, seguindo as regras do projeto.
Siga na ordem. Limite total de 3 tentativas por tarefa; na terceira falha, pare e reporte.

## 1. Decida (grátis, sem modelo)
`bash bin/kuru route "<tarefa>" --files <arquivos que você já sabe>` e leia o JSON:
- `acao: direto`: faça você mesmo, sem agente. Se vier `delegar_se`, só delegue quando essa condição for verdadeira.
- `acao: agente`: siga o passo 3. `incerta: true` significa sinal fraco; na dúvida, assuma o tier de cima.
- `risco: true`: tarefa de risco alto; o DeepSeek fica de fora da cadeia.

## 1b. Onde trabalhar (o usuário pode estar editando na IDE)
Tarefa longa ou que demora: `bash bin/kuru worktree create <id>` (JSON com `path`, `branch`, `base`). Todo o resto roda lá; a árvore principal é do usuário e o worktree nasce do último commit, sem as edições não commitadas dele. Tarefa curta na árvore principal: confira `git status --short` antes e não toque em arquivo sujo que não é seu.

## 2. Briefing autocontido
O agente começa sem contexto: nunca cole a conversa. Gere o briefing:
`bash bin/kuru brief --task "<o que fazer>" --files <arquivos> --criteria "<critério de pronto>" --tests "<comando de teste>" [--workdir <path do worktree>] --out .kuru/<tarefa>.prompt`
Com worktree, passe sempre `--workdir`. Ele inclui as regras do projeto por extenso. Passe o texto do briefing como prompt do subagent.
Peça sempre resposta curta (até 15 linhas): o que volta ao seu contexto também custa token.

## 3. Execute
- **complexa**: chame `planner` com o briefing e peça um plano de até 25 linhas; depois implemente você mesmo ou com `implementer-sonnet` (briefing + plano).
- **explorar muito** (`delegar_se`): `implementer-sonnet` com o briefing.
- **mecânica repetida em muitos arquivos**: `implementer-haiku`.
- **longa**: `planner` com o briefing (plano de até 25 linhas, já separando os arquivos em grupos independentes). Depois rode de 3 a 5 `implementer-sonnet` em paralelo, UMA chamada por grupo na mesma resposta, cada um com o seu briefing (só os arquivos do grupo + o trecho do plano) e sem se sobrepor nos arquivos. Reserva: se o limite do Claude acabar e a tarefa não tiver `risco`, `deepseek-coder` (ele chama a API com a chave do ambiente e devolve um diff validado; falha de chave, saldo ou limite, códigos 2, 3, 76, ou código 4 sem diff válido conta como tentativa). Se nada estiver disponível, pare e reporte.

## 4. Verifique
`bash bin/kuru check-rules` e a suíte de testes do projeto (com worktree, rode dentro dele). Falhou: corrija (conta como tentativa).

## 5. Revise (só mudança NÃO trivial)
Mudança trivial: o passo 4 basta. Senão: `git diff HEAD | bash bin/kuru review-flow check --task <id>` (inclua arquivos novos com `git add -N .`). Com worktree, o diff é o dele: `git -C <path> add -N .` e `git -C <path> diff <base>` (a `base` veio do `worktree create`). Leia o JSON:
- `verdict: APROVADO`: diff pequeno, as regras fixas bastam. Fim.
- `verdict: PARAR`: pare e reporte as 3 tentativas.
- `stage: deterministic` e `REPROVADO`: corrija as `violations` e repita. Nenhum modelo foi gasto. Se vier `next: PARAR` (3ª reprovação), pare e reporte.
- `verdict: PENDENTE`: chame o agente indicado em `agent` (`reviewer` ou `reviewer-senior`) uma vez por item de `packets`, colando o pacote INTEIRO (o campo `packet`, com as regras e o diff) INLINE no prompt, nunca um resumo (o revisor reprova entrada sem diff); nunca passe caminho de arquivo. O revisor reprova se qualquer pacote reprovar. Registre o veredito uma vez: `bash bin/kuru review-flow record --task <id> --stage <agent> --verdict APROVADO|REPROVADO`. `next: FIM` termina; `CORRIGIR` volta ao passo 3 (o `proximo_revisor` já considera a escalada ao Opus após 2 reprovações do Haiku); `PARAR` reporta.
`--model-review` no `check` exige revisor de modelo mesmo para diff pequeno.

## 6. Entregue (só com worktree)
Aprovado: commite no worktree (`git -C <path> add <seus caminhos>` e `git -C <path> commit`) e entregue a branch `kuru/<id>` ao usuário com o comando `git merge kuru/<id>` (`bash bin/kuru worktree status` mostra). Não mescle na árvore principal sem ele pedir. O `worktree remove` só roda depois de mesclado.

Termine dizendo: tier, quem executou, tentativas, o veredito da revisão e, se houve worktree, a branch.
