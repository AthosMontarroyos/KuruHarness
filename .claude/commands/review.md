---
description: Revisa um diff pelo fluxo da Fase 2 (determinístico, reviewer Haiku, reviewer-senior Opus)
argument-hint: <task-id> [base-ref, padrão HEAD]
---
Revise as mudanças da tarefa `$1` seguindo SEMPRE esta ordem. Não pule etapas e não leia o projeto inteiro.

1. Gere o diff: `git diff ${2:-HEAD}` (inclua arquivos novos com `git add -N .` se preciso).
2. Rode `git diff ${2:-HEAD} | python3 -m harness.review_flow check --task $1` e leia o JSON.
   - `verdict: PARAR`: pare, reporte ao usuário o que falhou nas 3 tentativas. Não tente uma quarta.
   - `stage: deterministic` com `REPROVADO`: corrija as `violations` e volte ao passo 1. Nenhum modelo foi gasto.
   - `verdict: PENDENTE`: siga para o passo 3.
3. Chame o sub-agent indicado em `agent` (`reviewer` ou `reviewer-senior`) uma vez para CADA item de `packets`, colando o texto do pacote INLINE no prompt. Nunca passe caminho de arquivo nem peça para ele ler nada: os revisores não têm ferramentas e não recebem o CLAUDE.md (regra 3 do SPEC). Se `packets` tiver mais de um item, o veredito da rodada é REPROVADO se qualquer pacote for reprovado, e APROVADO só se todos forem aprovados.
4. Registre o veredito da rodada uma única vez: `python3 -m harness.review_flow record --task $1 --stage <agent> --verdict APROVADO|REPROVADO`.
   - `next: FIM`: revisão concluída.
   - `next: CORRIGIR`: corrija com base nos motivos e volte ao passo 1 (o `proximo_revisor` já considera a escalada).
   - `next: PARAR`: reporte ao usuário.
Mostre ao final o veredito, os motivos e quantas tentativas foram usadas.
