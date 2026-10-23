# SPEC.md — especificação do harness

## Objetivo
Orquestrar sub-agents com custo controlado: planejar com modelo forte, revisar com modelo barato, escalar só quando necessário.

## Fases e critérios de pronto
| Fase | Escopo | Pronto quando |
|---|---|---|
| 0 Base | `CLAUDE.md`, `SPEC.md`, `TASKS.md`; Worker `kuru-subagents` como MCP exigindo token; Cursor CLI (`agent`) instalado e logado | Claude Code lista as ferramentas do MCP e responde a um "ping" |
| 1 Núcleo | Subagents `planner` (Opus), `reviewer` (Haiku), `quick-decider` (Haiku, esforço baixo) em `.claude/agents/`; hook de fim de tarefa (testes, linter, typecheck); limites | Uma tarefa real vai de plano a teste verde |
| 2 Conformidade | Checagens determinísticas → `reviewer` → escalada ao Opus só após 2 reprovações; revisor vê só diff + regras relevantes | Reprova de propósito um diff que viola este `SPEC.md` |
| 3 Cursor | `agent -p --trust` em git worktree separado, modo Agent; diff volta ao Claude Code | Tarefa longa volta como diff revisado |
| 4 Jev | Porteiro antes do revisor; baixa confiança escala ao Haiku | 50–100 diffs rotulados: acurácia aceitável nos casos de alta confiança |
| 5 DeepSeek | Reserva (limite do plano estourado ou tarefa não sensível) | Patch aplicado pelo Claude Code a partir do texto devolvido |
| 6 Medição | Log por tarefa: modelo, tokens, resultado, tentativas | Regras de roteamento ajustadas com dados |

## Limites
- Máximo 3 tentativas por tarefa.
- Teto de custo por tarefa: **a definir pelo usuário** (valor ainda não informado).
- Cursor: no máximo 3 processos em paralelo; sessão nova a cada tarefa (bug do `--resume`).

## Regras verificáveis pelo revisor
1. Nenhum segredo/token em arquivos versionados.
2. Todo subagent declara `model` explicitamente no frontmatter.
3. O revisor nunca recebe o projeto inteiro, só diff + regras.
4. Nenhuma fase é marcada concluída em `TASKS.md` sem o critério de pronto registrado.
5. Máximo de 3 tentativas por tarefa respeitado.
