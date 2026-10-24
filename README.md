# KuruHarness

Kit de subagents para o **Claude Code**, distribuído como plugin. Roteia cada tarefa pelo tamanho, implementa com o modelo certo, revisa o diff em 3 estágios e registra o resultado.

## Instalação

Passos para instalar o kit no Claude Code, pensados para o Claude executar a pedido do usuário (ou para o usuário rodar à mão). Sem clonar o repositório:

1. **Confira o ambiente**: `claude --version` (precisa de 2.1.292 ou mais novo), `python3 --version` (ou `python`, ou `py`; qualquer Python 3) e `git --version`.
2. **Instale o plugin** pelo shell:
   ```
   claude plugin install kuru-harness --marketplace AthosMontarroyos/KuruHarness
   ```
   Se o `claude` for mais antigo que 2.1.292 (e tiver pelo menos 2.1.275): `claude plugin marketplace add AthosMontarroyos/KuruHarness` e depois `claude plugin install kuru-harness@kuru`.
3. **Confirme**: `claude plugin details kuru-harness` deve listar **6 Agents, 3 Skills e 1 Hook** (os 3 comandos aparecem como Skills no `details`). Se listar menos, pare e mostre a saída ao usuário.
4. **Avise o usuário** que ele precisa rodar `/reload-plugins` (ou reiniciar a sessão) e que os comandos novos são:
   - `/kuru-harness:task <id> <descrição>`: roteia, implementa, verifica e revisa uma tarefa;
   - `/kuru-harness:review <id>`: revisa o diff atual (regras fixas, depois Haiku, depois Opus só após 2 reprovações);
   - `/kuru-harness:fallback <id> <descrição>`: faz uma tarefa não sensível pelo DeepSeek.
5. **Teste rápido** (opcional): `kuru route "corrigir typo" --files a.md` deve devolver `{"tier": "trivial", ...}`.

### Cuidados
- A instalação não precisa clonar este repositório, copiar arquivos dele para o projeto nem rodar scripts baixados.
- Chaves, tokens e senhas não vão para arquivo nenhum. Para usar o Cursor, a chave vai só na variável de ambiente `CURSOR_API_KEY`; `agent login` só se o usuário pedir.
- O `CLAUDE.md`, o `settings.json` e as permissões do usuário só mudam com o "sim" dele. Duas sugestões para oferecer:
  - Regras de permissão, porque um plugin não consegue trazê-las e, sem elas, cada passo do `/kuru-harness:task` pede aprovação. Acrescentar a `~/.claude/settings.json`:
    ```json
    { "permissions": { "allow": [ "Bash(kuru *)", "Bash(git diff*)", "Bash(git status*)", "Bash(git apply*)", "Bash(git add -N*)" ] } }
    ```
  - Atualização automática: marketplaces de terceiros vêm com ela desligada. Ligar em `/plugin` → aba Marketplaces → `kuru` → Enable auto-update. Sem isso, atualizar com `claude plugin update kuru-harness@kuru`.

### Se algo falhar
- **Windows**: o Claude Code roda os comandos com o Git Bash. O `kuru` procura `python3`, `python` e `py` e testa cada um, ignorando o `python3` da Microsoft Store (que não roda nada). Se der erro, mostre a mensagem inteira ao usuário.
- **Sessões na nuvem (claude.ai/code) não carregam plugins.** Avise o usuário se for esse o caso.
- `claude plugin marketplace remove kuru` desinstala tudo.

## Peças opcionais (o plugin funciona sem elas)
- **Cursor CLI** para tarefas longas: precisa do `agent` instalado e logado. O modelo é fixo em `grok-4.7-high-fast` (o padrão da conta é `auto`); confira com `agent models`.
- **DeepSeek e Jev** vêm do servidor MCP `kuru-subagents`, que é do usuário e não faz parte do plugin. Sem ele, a cadeia de codificadores pula o DeepSeek e vai direto ao Sonnet.

## Mapa do repositório
- `agents/`, `commands/`, `hooks/`, `bin/kuru`: o plugin (subagents, comandos, hook de fim de tarefa e o launcher que acha o Python).
- `.claude-plugin/`: manifestos do plugin e do marketplace.
- `harness/`, `scripts/`: roteador, revisão, checagem de regras, log e runner do Cursor.
- `CLAUDE.md`, `SPEC.md`, `TASKS.md`: regras, especificação e ledger de quem **desenvolve** este kit.
- `tests/`: `python -m unittest discover -s tests -t .`. Para desenvolver: `claude --plugin-dir .`.
