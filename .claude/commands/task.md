---
description: Executa uma tarefa pelo fluxo completo (roteamento, planner se preciso, implementação, checagens, /review)
argument-hint: <task-id> <descrição da tarefa em linguagem natural> (cite os arquivos se souber)
---
Argumentos recebidos: `$ARGUMENTS`. A primeira palavra é o task-id; o resto é a descrição da tarefa (e, se citados, os arquivos). Separe os três antes de começar. Execute a tarefa pelo fluxo abaixo. Máximo de 3 tentativas no total; na 3ª falha, pare e reporte.

1. **Roteie**: `python3 -m harness.route "<descrição>" --files <arquivos que você já sabe que serão tocados>` e leia o JSON (`tier`, `agents`, `incerta`).
   - Se `incerta` for `true`: pergunte ao `quick-decider` (Haiku) o tamanho da tarefa. Opcional: `ask_jev` com as perguntas de `python3 -m harness.route "<descrição>" --jev-questions` — o Jev só pode SUBIR o tier, nunca baixar, e nunca decida só por ele.
2. **Planeje** só se `agents` começar por `planner`: chame o `planner` (Opus) com a descrição e os arquivos; uma chamada por subtarefa, contexto isolado.
3. **Implemente** com o agent indicado (`implementer-haiku` ou `implementer-sonnet`). Se for `cursor` e o `agent` do Cursor não existir nesta máquina, use `planner` + `implementer-sonnet`.
4. **Verifique**: `python3 -m harness.check_rules` e a suíte de testes. Falhou? Volte ao passo 3 com o erro (conta como tentativa).
5. **Revise**: rode `/review <task-id>`. Reprovado? Corrija e repita (a escalada ao Opus e o limite de 3 já estão no fluxo).
6. O hook de fim de tarefa grava o resultado no log (`python3 -m harness.tasklog summary`).
Mostre ao final: tier escolhido, agents usados, tentativas e o veredito da revisão.
