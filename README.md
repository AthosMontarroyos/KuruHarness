# KuruHarness

Kit de subagents para o **Claude Code**: roteia cada tarefa pelo tamanho, implementa com o modelo certo, revisa o diff em 3 estágios e registra o resultado.

## Como usar

Abra o Claude Code **dentro deste repositório**. Tudo vale sem instalar nada: subagents e comandos (`/task`, `/review`, `/fallback`) ficam em `.claude/`, o `CLAUDE.md` carrega sozinho (inclusive o formato do `ask_jev`) e o hook de fim de tarefa vem de `.claude/settings.json`.

Para levar o kit a outro projeto, copie `.claude/agents/`, `.claude/commands/`, `harness/`, `bin/` e `scripts/`, e junte as regras do `CLAUDE.md` e o bloco `hooks`/`permissions` do `.claude/settings.json` aos seus. Os comandos chamam o launcher por `bash bin/kuru`, então `bin/` precisa estar na raiz do projeto.

## Requisitos
- Python 3 (o `bin/kuru` testa `python3`, `python` e `py` e ignora o atalho quebrado da Microsoft Store no Windows) e Git. No Windows, o Claude Code roda os comandos pelo Git Bash.
- Opcionais: **Cursor CLI** (`agent`) para tarefas longas, com o modelo fixo em `grok-4.7-high-fast` (o padrão da conta é `auto`; confira com `agent models`); e o servidor MCP `kuru-subagents` (DeepSeek e Jev), que é do usuário e não faz parte deste repo. Sem ele, a cadeia de codificadores pula o DeepSeek e vai ao Sonnet.

## Mapa
- `.claude/agents/`, `.claude/commands/`, `.claude/settings.json`: o kit.
- `harness/`, `scripts/`, `bin/kuru`: roteador, revisão, checagem de regras, log e runner do Cursor.
- `CLAUDE.md`, `SPEC.md`, `TASKS.md`: regras, especificação e ledger.
- `tests/`: `python -m unittest discover -s tests -t .`.

## Por que não é plugin
Foi plugin por um tempo (PR #5) e saiu: todo comando e agent ganhava prefixo, um plugin não carrega o `CLAUDE.md` (e o Claude deixava de saber o formato do Jev) e não traz regras de permissão. Está no histórico do git.
