# Casos rotulados (Fase 4)

Cada `cases_*.json` é uma lista de `{id, rule, label, diff, note}`.
- `label`: `violates` ou `ok`. `rule`: regra violada (`R1`, `R2`, `R4`, `R5`) ou `none`.
- Os rótulos são sintéticos (definidos na criação do caso). Uma amostra deve ser conferida por humano.

Regras avaliadas:
- R1: nenhum segredo/token literal em arquivo versionado.
- R2: todo subagent em `.claude/agents/*.md` declara `model` no frontmatter.
- R4: nenhuma fase é marcada `[x]` em `TASKS.md` sem o critério de pronto registrado na mesma linha.
- R5: o máximo de tentativas por tarefa é 3 (`MAX_ATTEMPTS = 3`, hook e `tasklog` respeitam).
