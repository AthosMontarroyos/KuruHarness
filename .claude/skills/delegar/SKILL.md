---
name: delegar
description: Procedimento exato para delegar uma tarefa NÃO trivial a subagents ou ao Cursor (roteamento, briefing autocontido, cadeia de codificadores, revisão em 3 estágios). Use antes de delegar. Não use para tarefa trivial: nesse caso faça você mesmo, sem agente.
---
Siga na ordem. Limite total de 3 tentativas por tarefa; na terceira falha, pare e reporte.

## 1. Decida (grátis, sem modelo)
`bash bin/kuru route "<tarefa>" --files <arquivos que você já sabe>` e leia o JSON:
- `acao: direto`: faça você mesmo, sem agente. Se vier `delegar_se`, só delegue quando essa condição for verdadeira.
- `acao: agente`: siga o passo 3. `incerta: true` significa sinal fraco; na dúvida, assuma o tier de cima.
- `risco: true`: tarefa de risco alto; o DeepSeek fica de fora da cadeia.

## 2. Briefing autocontido
O agente começa sem contexto: nunca cole a conversa. Gere o briefing:
`bash bin/kuru brief --task "<o que fazer>" --files <arquivos> --criteria "<critério de pronto>" --tests "<comando de teste>" --out .kuru/<tarefa>.prompt`
Ele inclui as regras do projeto por extenso. Para um subagent, passe o texto do briefing como prompt; para o Cursor, o arquivo.
Peça sempre resposta curta (até 15 linhas): o que volta ao seu contexto também custa token.

## 3. Execute
- **complexa**: chame `planner` com o briefing e peça um plano de até 25 linhas; depois implemente você mesmo ou com `implementer-sonnet` (briefing + plano).
- **explorar muito** (`delegar_se`): `implementer-sonnet` com o briefing.
- **mecânica repetida em muitos arquivos**: `implementer-haiku`.
- **longa** (cadeia, descendo só quando o anterior estiver INDISPONÍVEL; reprovação ou teste falho não desce, conta como tentativa):
  1. Cursor: `bash bin/kuru cursor-task <id> .kuru/<id>.prompt` (worktree isolado, `grok-4.7-high-fast`, no máximo 3 em paralelo). Saída 0: leia `.claude/state/cursor/<id>.diff`, valide com `git apply --check`, revise (passo 5) e só então `git apply`; depois `bash bin/kuru cursor-task --clean <id>`. Saída ≠ 0 (76 = provável falta de saldo ou limite, 75 = sem vaga, 127 = CLI ausente) = Cursor indisponível: avise o usuário e desça. Código 2 = argumento ou prompt inválido (sem regras, vazio ou worktree já existente): corrija o briefing ou rode `--clean`, e conta como tentativa. Qualquer outro código é falha do próprio `agent`: leia o log; se for login ou autenticação ausente, é indisponível e você desce; senão conta como tentativa. Depois de qualquer falha, rode `bash bin/kuru cursor-task --clean <id>` antes de tentar de novo (worktree existente sai com 2).
  2. `deepseek-coder` (só sem `risco`): ele chama a API com a chave do ambiente e devolve um diff validado. Falha de chave, saldo ou limite (códigos 2, 3, 76): desça. Código 4 (sem diff válido) conta como tentativa, não desce.
  3. `planner` e depois `implementer-sonnet`. Se o plano do Claude também estiver no limite, pare e reporte.

## 4. Verifique
`bash bin/kuru check-rules` e a suíte de testes do projeto. Falhou: corrija (conta como tentativa).

## 5. Revise (só mudança NÃO trivial)
Mudança trivial: o passo 4 basta. Senão: `git diff HEAD | bash bin/kuru review-flow check --task <id>` (inclua arquivos novos com `git add -N .`). Leia o JSON:
- `verdict: APROVADO`: diff pequeno, as regras fixas bastam. Fim.
- `verdict: PARAR`: pare e reporte as 3 tentativas.
- `stage: deterministic` e `REPROVADO`: corrija as `violations` e repita. Nenhum modelo foi gasto. Se vier `next: PARAR` (3ª reprovação), pare e reporte.
- `verdict: PENDENTE`: chame o agente indicado em `agent` (`reviewer` ou `reviewer-senior`) uma vez por item de `packets`, colando o pacote INLINE no prompt; nunca passe caminho de arquivo. O revisor reprova se qualquer pacote reprovar. Registre o veredito uma vez: `bash bin/kuru review-flow record --task <id> --stage <agent> --verdict APROVADO|REPROVADO`. `next: FIM` termina; `CORRIGIR` volta ao passo 3 (o `proximo_revisor` já considera a escalada ao Opus após 2 reprovações do Haiku); `PARAR` reporta.
`--model-review` no `check` exige revisor de modelo mesmo para diff pequeno.

Termine dizendo: tier, quem executou, tentativas e o veredito da revisão.
