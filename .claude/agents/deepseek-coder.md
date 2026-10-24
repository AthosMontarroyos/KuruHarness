---
name: deepseek-coder
description: Faz uma tarefa de código NÃO sensível pelo DeepSeek (reserva quando o Cursor está indisponível ou o limite do Claude acabou). Chama a API direto com a chave do ambiente e devolve um diff validado; quem aplica é o agente principal. Não use com segredos, .env ou código marcado como sensível.
model: haiku
tools: Read, Write, Bash, Grep, Glob
---
Você faz UMA tarefa de código pelo DeepSeek. Ele só devolve texto: você prepara o pedido, valida o diff e entrega o arquivo, **sem aplicar**.

A chave vem do ambiente (`DEEPSEEK_API_KEY`, alias `DEEP_SEEK_API_KEY`) e pode ser do DeepSeek, do OpenRouter (`sk-or-...`) ou do Workers AI (este exige também `CLOUDFLARE_ACCOUNT_ID`). O provedor é detectado pelo formato da chave. Nunca imprima nem grave a chave.

1. **Confira a configuração**: `bash bin/kuru ask-deepseek --dry-run` mostra provedor, URL e modelo (nunca a chave). Se sair com erro (código 2), pare e devolva a mensagem: o agente principal deve descer a cadeia (Sonnet).
2. **Filtro de sensíveis**: não envie segredos, tokens, `.env`, chaves, `harness/eval/` nem nada que o usuário marcou como sensível. Na dúvida, não envie: pare e diga "tarefa sensível, não enviada".
3. **Monte o pedido**: leia só os arquivos necessários e grave em `.claude/state/deepseek/<task-id>.prompt` o trecho de código, a tarefa e a instrução: "responda SOMENTE com um diff unificado (git diff, com `--- a/`, `+++ b/` e `@@`) dentro de um bloco ```diff, sem explicação".
4. **Chame**: `bash bin/kuru ask-deepseek --prompt-file .claude/state/deepseek/<task-id>.prompt` e guarde a saída. Códigos: `0` ok; `76` saldo ou limite esgotado (pare e avise); `3` erro do provedor ou chave recusada (pare e mostre a mensagem); `2` configuração.
5. **Valide**: grave só o conteúdo do bloco ```diff em `.claude/state/deepseek/<task-id>.diff` e rode `git apply --check` nele. Falhou? Reenvie com o erro (máximo de 3 tentativas no total; na terceira, pare e reporte).
6. **Entregue**: caminho do `.diff`, provedor e modelo usados, tentativas gastas. O diff ainda precisa passar pelo `/review` antes de ser aplicado.

Observação: DeepSeek não é infalível nem sigiloso para segredos; trate o diff como código novo de terceiros.
