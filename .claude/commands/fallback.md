---
description: Faz uma tarefa NÃO sensível pelo DeepSeek (reserva quando o limite do Claude estoura). Ele só devolve texto; quem aplica o patch é o Claude Code
argument-hint: <task-id> <descrição da tarefa> (cite os arquivos)
---
Argumentos: `$ARGUMENTS` (primeira palavra = task-id). Use SÓ para tarefa não sensível e quando o limite do plano Claude estourar ou o usuário pedir. O DeepSeek tem US$ 5/mês de teto (o Worker bloqueia sozinho; `budget_status` mostra o gasto).

1. **Filtro**: não envie segredos, tokens, `.env`, nada de `harness/eval` nem código que o usuário marcou como sensível. Na dúvida, não envie.
2. Leia os arquivos da tarefa e monte UM prompt com o trecho necessário e a tarefa. Peça: "responda SOMENTE com um diff unificado (git diff, --- a/ +++ b/ e @@) num bloco ```diff, sem explicação".
3. Chame `ask_deepseek` com esse prompt. Se vier "Teto mensal do DeepSeek atingido", pare e avise o usuário.
4. Extraia o diff do bloco para um arquivo e valide: `git apply --check <arquivo>`. Falhou? Reenvie com o erro (conta como tentativa; máximo de 3).
5. Aplique (`git apply`), rode `python3 -m harness.check_rules` e a suíte de testes, e depois `/review <task-id>`. Não confie no DeepSeek mais do que em qualquer código novo: o `/review` é obrigatório.
Mostre ao final: arquivos alterados, tentativas usadas e o veredito da revisão.
