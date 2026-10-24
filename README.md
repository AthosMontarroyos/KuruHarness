# KuruHarness

Kit de subagents para o **Claude Code**. O Claude decide **sozinho** quando delegar: não há comando para digitar. A política está no `CLAUDE.md` (curta, carregada a cada turno) e o procedimento detalhado na skill `delegar` (o Claude a aciona quando precisa).

## Como funciona
- **Trivial, o Claude faz direto.** Delegar custa tokens (prompt do agente, briefing e resposta); só compensa quando poupa o contexto principal ou melhora a qualidade.
- **Delega quando vale:** explorar muito (`implementer-sonnet`), tarefa complexa (`planner` primeiro), tarefa longa (Cursor), mudança mecânica em lote (`implementer-haiku`), revisão independente de mudança não trivial (`reviewer`, depois `reviewer-senior` só após 2 reprovações).
- **Isolamento:** todo agente começa sem contexto e recebe só um briefing autocontido (`bash bin/kuru brief`), nunca a conversa. Cada um roda com `omitClaudeMd` e carrega o que precisa na própria definição.
- **Cursor:** não lê o `CLAUDE.md`, então o briefing leva as regras do projeto por extenso e `bin/kuru cursor-task` recusa um prompt sem elas.
- **Revisão:** diff pequeno (1 arquivo, até 20 linhas) passa só pelas regras fixas, sem gastar modelo.

## Agentes
| Agente | Modelo | Quando |
|---|---|---|
| `planner` | Opus | tarefa complexa, antes de codar |
| `implementer-sonnet` | Sonnet | exploração grande que encheria o contexto |
| `implementer-haiku` | Haiku | mesma mudança mecânica em muitos arquivos |
| `reviewer` / `reviewer-senior` | Haiku / Opus | revisão de mudança não trivial (só diff + regras) |
| `quick-decider` | Haiku | dúvida de uma frase |
| `auditor` | Haiku 5.5 (1M nativo) | confere instruções do projeto contra o código e propõe o que mudar (só leitura) |
| `deepseek-coder` | Haiku | reserva barata, só texto (chave de ambiente) |
| `jev-judge` | Haiku | triagem de baixo risco por probabilidades (chave de ambiente) |
| `creative` | Sonnet | imagem e vídeo pela Higgsfield (chave de ambiente, gasta crédito) |

## Chaves (variáveis de ambiente)
| Variável | Para quê | Observação |
|---|---|---|
| `DEEPSEEK_API_KEY` (ou `DEEP_SEEK_API_KEY`) | `deepseek-coder` | chave do DeepSeek, do OpenRouter (`sk-or-...`) ou do Workers AI; o provedor é detectado pelo formato |
| `JEV_API_KEY` | `jev-judge` | chave do Workers AI (o Jev estruturado só existe lá) |
| `CLOUDFLARE_ACCOUNT_ID` | Workers AI | necessário quando alguma chave for do Workers AI |
| `HIGGSFIELD_API_KEY` | `creative` | cada geração gasta crédito e só roda com aprovação do usuário |
| `CURSOR_API_KEY` | `bin/kuru cursor-task` | opcional |

Para trocar provedor ou modelo: `DEEPSEEK_PROVIDER`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `JEV_BASE_URL`, `JEV_MODEL`. Para conferir sem gastar: `bash bin/kuru ask-deepseek --dry-run`, `bash bin/kuru ask-jev --dry-run`.

**No Claude Code na nuvem**: menu do ambiente na barra de título da sessão → *Edit* → *Network secrets* (ou variável de ambiente, se a seção não aparecer). Uma sessão nova já enxerga. Nunca cole uma chave no chat. Em *Network access*, libere `api.deepseek.com`, `openrouter.ai`, `api.cloudflare.com` e `api.higgsfield.ai`.

## Usar
Abra o Claude Code dentro do repositório. Para levar o kit a outro projeto, copie `.claude/agents/`, `.claude/skills/`, `harness/`, `bin/` e `scripts/`, e junte as regras do `CLAUDE.md` e o bloco `hooks`/`permissions` do `.claude/settings.json` aos seus (`bin/` fica na raiz do projeto: o kit chama o launcher por `bash bin/kuru`).

Requisitos: Python 3 (o `bin/kuru` testa `python3`, `python` e `py` e ignora o atalho quebrado da Microsoft Store no Windows) e Git; no Windows, o Claude Code roda os comandos pelo Git Bash. Opcional: Cursor CLI (`agent`), com o modelo fixo em `grok-4.7-high-fast` (o padrão da conta é `auto`; confira com `agent models`).

## Mapa
`.claude/agents/` e `.claude/skills/` (o kit), `.claude/settings.json` (hook e permissões), `harness/` e `bin/kuru` (roteador, briefing, revisão, regras, log, chamadas de API), `scripts/` (hook e runner do Cursor), `CLAUDE.md`/`SPEC.md`/`TASKS.md` (regras, especificação e ledger), `tests/` (`python -m unittest discover -s tests -t .`).

Já foi plugin (PR #5) e saiu: exigia prefixo em tudo e não carregava o `CLAUDE.md`. Está no histórico do git.
