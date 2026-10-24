# KuruHarness

Harness de sub-agents para Claude Code (e Cursor CLI para coding longo), com apoio do Worker MCP `kuru-subagents`.

- `CLAUDE.md`: regras do projeto
- `SPEC.md`: especificação, fases e critérios de pronto
- `TASKS.md`: ledger compartilhado
- `agents/`, `commands/`, `hooks/`, `bin/kuru`: o plugin (subagents, comandos, hook de fim de tarefa e launcher)
- `.claude-plugin/`: manifesto do plugin e do marketplace
- `scripts/`: hook de fim de tarefa (testes, regras, log) e o runner do Cursor
- `codex/`: instruções, skills e pets do Codex, mantidos como referência (`instrucoes.md`, `skills/`, `pets/`)

## Instalar como plugin do Claude Code (Windows, macOS e Linux)

Sem clonar este repo e sem `curl | bash`. No terminal (Claude Code 2.1.292 ou mais novo):

```bash
claude plugin install kuru-harness --marketplace AthosMontarroyos/KuruHarness
```

Ou dentro de uma sessão (2.1.275+): `/plugin install kuru-harness --marketplace AthosMontarroyos/KuruHarness`. Isso instala 6 subagents, 3 comandos (`/kuru-harness:task`, `/kuru-harness:review`, `/kuru-harness:fallback`), o hook de fim de tarefa e o comando `kuru` no PATH. Reinicie a sessão (ou `/reload-plugins`).

**Requisitos**: Python 3 e Git. No Windows, o Claude Code roda os comandos com o Git Bash. O `kuru` procura `python3`, `python` e `py` e testa cada um (o `python3` da Microsoft Store não roda nada e é ignorado).

**Atualização**: marketplaces de terceiros vêm com a atualização automática DESLIGADA. Ligue em `/plugin` → aba Marketplaces → `kuru` → Enable auto-update, ou rode `claude plugin update kuru-harness@kuru`.

**Permissões**: um plugin não pode trazer regras de permissão. Para o `/kuru-harness:task` não pedir aprovação a cada passo, acrescente ao seu `~/.claude/settings.json`:

```json
{ "permissions": { "allow": [ "Bash(kuru *)", "Bash(git diff*)", "Bash(git status*)", "Bash(git apply*)", "Bash(git add -N*)" ] } }
```

**Para o time**: `claude plugin install kuru-harness@kuru --scope project` grava o plugin em `.claude/settings.json`. Commitar isso liga o plugin para os colegas, mas cada um ainda roda o `install` uma vez.

**Não funciona em sessões na nuvem** (claude.ai/code): elas não carregam plugins.

**Desenvolvimento deste repo**: `claude --plugin-dir .` carrega o plugin direto da pasta.
