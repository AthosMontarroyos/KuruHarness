---
description: Executa uma tarefa pelo fluxo completo (roteamento, planner se preciso, implementação, checagens, /review)
argument-hint: <task-id> <descrição da tarefa em linguagem natural> (cite os arquivos se souber)
allowed-tools: Bash(bash bin/kuru *), Bash(git diff*), Bash(git status*), Bash(git apply*)
---
Argumentos recebidos: `$ARGUMENTS`. A primeira palavra é o task-id; o resto é a descrição da tarefa (e, se citados, os arquivos). Separe os três antes de começar. Execute a tarefa pelo fluxo abaixo. Máximo de 3 tentativas no total; na 3ª falha, pare e reporte.


1. **Roteie**: `bash bin/kuru route "<descrição>" --files <arquivos que você já sabe que serão tocados>` e leia o JSON (`tier`, `agents`, `incerta`).
   - Se `incerta` for `true`: pergunte ao `quick-decider` (Haiku) o tamanho da tarefa. Opcional: `ask_jev` com as perguntas de `bash bin/kuru route "<descrição>" --jev-questions` — o Jev só pode SUBIR o tier, nunca baixar, e nunca decida só por ele.
2. **Planeje** só se `agents` começar por `planner`: chame o `planner` (Opus) com a descrição e os arquivos; uma chamada por subtarefa, contexto isolado.
3. **Implemente** com o agent indicado (`implementer-haiku` ou `implementer-sonnet`). Se `agents` for `["cursor"]` (tarefa longa), siga a **cadeia de codificadores** do campo `cadeia`, descendo para o próximo só quando o anterior estiver INDISPONÍVEL (falha de infraestrutura), não quando ele errou a tarefa:
   1. **Cursor**: salve o prompt (tarefa + arquivos + critério de pronto) em `.kuru/cursor/<task-id>.prompt` (use a ferramenta Write; `.claude/` é protegida) e rode `bash bin/kuru cursor-task <task-id> .kuru/cursor/<task-id>.prompt` (worktree isolado, modelo `grok-4.7-high-fast`, no máximo 3 em paralelo). Saída 0: leia `.claude/state/cursor/<task-id>.diff`, valide com `git apply --check`, aplique com `git apply` e rode `bash bin/kuru cursor-task --clean <task-id>`. Qualquer saída diferente de 0 (76 = provável falta de saldo/limite, 75 = sem vaga, 127 = CLI ausente, deslogado, erro do agent) significa Cursor indisponível: avise o usuário do motivo e desça.
   2. **DeepSeek** (só se `cadeia` ainda tiver `deepseek`, ou seja, tarefa sem risco alto): chame o agent `deepseek-coder` com o `<task-id>`, a descrição e os arquivos. Ele usa a chave do ambiente (`DEEPSEEK_API_KEY`) e devolve um diff validado, que você aplica depois do `/review`. Erro de configuração, de chave ou saldo/limite esgotado (códigos 2, 3, 76): desça.
   3. **Claude**: `planner` (Opus) e depois `implementer-sonnet`. Sonnet e não Haiku: aqui só caem tarefas grandes, e o Haiku já cobre as triviais.
   Se o plano do Claude também estiver no limite, pare e reporte ao usuário. Reprovação na revisão ou teste falho NÃO desce a cadeia: conta como tentativa (máximo de 3 no total) com o mesmo codificador.
4. **Verifique**: `bash bin/kuru check-rules` e a suíte de testes. Falhou? Volte ao passo 3 com o erro (conta como tentativa).
5. **Revise**: rode `/review <task-id>`. Reprovado? Corrija e repita (a escalada ao Opus e o limite de 3 já estão no fluxo).
6. O hook de fim de tarefa grava o resultado no log (`bash bin/kuru tasklog summary`).
Mostre ao final: tier escolhido, agents usados, tentativas e o veredito da revisão.
