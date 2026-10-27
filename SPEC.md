# SPEC.md — especificação do harness

## Objetivo
Orquestrar sub-agents com custo controlado: planejar com modelo forte, revisar com modelo barato, escalar só quando necessário.

## Fases e critérios de pronto
| Fase | Escopo | Pronto quando |
|---|---|---|
| 0 Base | `CLAUDE.md`, `SPEC.md`, `TASKS.md`; Worker `kuru-subagents` como MCP exigindo token (depois substituído por chamada direta de API com chave de ambiente, ver R.15 em `TASKS.md`) | Claude Code lista as ferramentas do MCP e responde a um "ping" |
| 1 Núcleo | Subagents `planner` (Opus), `reviewer` (Haiku), `quick-decider` (Haiku, esforço baixo) em `.claude/agents/`; hook de fim de tarefa (testes, linter, typecheck); limites | Uma tarefa real vai de plano a teste verde |
| 2 Conformidade | Checagens determinísticas → `reviewer` → escalada ao Opus só após 2 reprovações; revisor vê só diff + regras relevantes | Reprova de propósito um diff que viola este `SPEC.md` |
| 3 Codificação em paralelo | `planner` divide a tarefa longa em grupos independentes de arquivos; de 3 a 5 `implementer-sonnet` em paralelo; diff revisado; roda em worktree isolado (`kuru worktree`) para não colidir com a edição do usuário na IDE (Cursor). O Cursor CLI chamado pelo Bash foi removido: Cursor e Claude só compartilham o repositório | Tarefa longa volta como branch `kuru/<id>` com diff revisado, sem tocar na árvore principal |
| 4 Jev | Julgador rápido de decisões no meio da tarefa (inclusive porteiro de diffs antes do revisor); baixa confiança escala ao Haiku | 50–100 casos rotulados: acurácia aceitável nos casos de alta confiança |
| 5 DeepSeek | REMOVIDA a pedido do usuário: o único modelo auxiliar é o Jev. Se o limite do Claude acabar, o trabalho para e é reportado | (histórico: R.15 e R.25 em `TASKS.md`) |
| 6 Medição | Log por tarefa: modelo, tokens, resultado, tentativas | Regras de roteamento ajustadas com dados |

## Limites
- Máximo 3 tentativas por tarefa.
- Teto de custo mensal: Higgsfield US$ 5. Jev sem teto: o usuário informa que não gera cobrança (AI Gateway recarregado com US$ 10). O kit não soma gasto: o limite real é o saldo pré-pago do provedor (chamada direta) e a aprovação do usuário. Ao esgotar o saldo (códigos 402/429, saída 76), o trabalho espera ou é reportado.
- Agentes em paralelo: de 3 a 5.

## Regras verificáveis pelo revisor
1. Nenhum segredo/token em arquivos versionados.
2. Todo subagent declara `model` explicitamente no frontmatter.
3. O revisor nunca recebe o projeto inteiro, só diff + regras.
4. Nenhuma fase é marcada concluída em `TASKS.md` sem o critério de pronto registrado.
5. Máximo de 3 tentativas por tarefa respeitado.
6. Higgsfield: teto de US$ 5, garantido pelo saldo pré-pago e pela aprovação do usuário (o kit não soma gasto).
