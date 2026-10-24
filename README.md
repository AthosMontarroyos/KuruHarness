# KuruHarness

Harness de sub-agents para Claude Code (e Cursor CLI para coding longo), com apoio do Worker MCP `kuru-subagents`.

- `CLAUDE.md`: regras do projeto
- `SPEC.md`: especificação, fases e critérios de pronto
- `TASKS.md`: ledger compartilhado
- `.claude/agents/`: `planner`, `reviewer`, `quick-decider`
- `scripts/end-of-task.sh`: hook de fim de tarefa (testes, linter, typecheck)
- `codex/`: instruções, skills e pets do Codex, mantidos como referência (`instrucoes.md`, `skills/`, `pets/`)

## Instalar o kit em outro projeto (sem clonar este repo)

No diretório do projeto onde você quer o kit:

```bash
curl -fsSL https://raw.githubusercontent.com/AthosMontarroyos/KuruHarness/main/install.sh | bash
```

Baixa só o tarball do GitHub (o repo é público, sem token), copia subagents, comandos, `harness/` e `scripts/`, e descarta o resto. `.claude/settings.json`, `CLAUDE.md`, `SPEC.md` e `.gitignore` do projeto são **mesclados** (blocos `kuru-harness`), nunca sobrescritos; rodar de novo atualiza o kit. Recusa instalar se já existir uma pasta `harness/` que não seja do kit. Depois, reinicie a sessão do Claude Code e confie no projeto uma vez. Para fixar uma versão: `KURU_REF=<tag ou commit>`.

Para instalar sozinho ao abrir uma sessão (por exemplo no Claude Code na nuvem), adicione ao `.claude/settings.json` do projeto:

```json
{ "hooks": { "SessionStart": [ { "hooks": [ { "type": "command",
  "command": "[ -f harness/route.py ] || curl -fsSL https://raw.githubusercontent.com/AthosMontarroyos/KuruHarness/main/install.sh | bash" } ] } ] } }
```

Os subagents e comandos só são carregados no começo da sessão, então na primeira vez pode ser preciso reiniciá-la.
