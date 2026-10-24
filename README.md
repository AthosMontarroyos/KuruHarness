# KuruHarness

Harness de sub-agents para Claude Code (e Cursor CLI para coding longo), com apoio do Worker MCP `kuru-subagents`.

- `CLAUDE.md`: regras do projeto
- `SPEC.md`: especificação, fases e critérios de pronto
- `TASKS.md`: ledger compartilhado
- `.claude/agents/`: `planner`, `reviewer`, `quick-decider`
- `scripts/end-of-task.sh`: hook de fim de tarefa (testes, linter, typecheck)
- `codex/`: instruções, skills e pets do Codex, mantidos como referência (`instrucoes.md`, `skills/`, `pets/`)
