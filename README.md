# KuruHarness

Kit de subagents para o **Claude Code**. O Claude decide **sozinho** quando delegar: não há comando para digitar. A política está no `CLAUDE.md` (curta, carregada a cada turno) e o procedimento detalhado na skill `delegar` (o Claude a aciona quando precisa).

## Como funciona
- **Trivial, o Claude faz direto.** Delegar custa tokens (prompt do agente, briefing e resposta); só compensa quando poupa o contexto principal ou melhora a qualidade.
- **Delega quando vale:** explorar muito (`implementer-sonnet`), tarefa complexa (`planner` primeiro), tarefa longa (`planner` e depois de 3 a 5 `implementer-sonnet` em paralelo), mudança mecânica em lote (`implementer-haiku`), revisão independente de mudança não trivial (`reviewer`, depois `reviewer-senior` só após 2 reprovações).
- **Isolamento:** todo agente começa sem contexto e recebe só um briefing autocontido (`bash bin/kuru brief`), nunca a conversa. Cada um roda com `omitClaudeMd` e carrega o que precisa na própria definição.
- **Revisão:** diff pequeno (1 arquivo, até 20 linhas alteradas, somando `+` e `-`) passa só pelas regras fixas, sem gastar modelo.

## Cursor + Claude (em paralelo)
A divisão é por **quem mexe em quê**, não por quem chama quem: você programa na IDE (Cursor, que lê as mesmas skills de `.claude/`) e, ao mesmo tempo, o Claude Code roda tarefas longas. O Claude **não chama o Cursor** (essa integração pelo Bash foi removida); os dois só compartilham o repositório.
- **A árvore principal é sua.** Antes de editar nela, o Claude confere `git status --short` e não toca em arquivo sujo que não é dele; nunca usa `stash`, `reset`, `checkout --`, `clean`, `add -A` nem `commit -a` ali.
- **Tarefa longa vai para um worktree isolado:** `bash bin/kuru worktree create <id>` cria `.kuru/worktrees/<id>` na branch `kuru/<id>` (index e arquivos próprios, sem conflito com a IDE). Ele nasce do **último commit**: o que você ainda não commitou não entra nele. O `planner` e os `implementer-sonnet` em paralelo trabalham só lá (o briefing leva `--workdir`).
- **Entrega = branch.** Quando a revisão aprova, o Claude commita no worktree e te passa `git merge kuru/<id>`. Quem mescla é você (ou ele, se você pedir). `bash bin/kuru worktree status` lista o que está pendente; `bash bin/kuru worktree remove <id>` recusa apagar trabalho sujo ou não mesclado (`--force` descarta).
- **O hook de fim de tarefa** confere o worktree ativo, então uma edição quebrada sua na IDE não reprova o Claude.
- **Limites:** só um worktree ativo por vez; o Cursor não roda o hook nem os subagents deste kit, então o que você escreve na IDE só passa pelas checagens se você rodar `bash bin/kuru check-rules` (ou pedir ao Claude para revisar o diff). A skill `delegar` avisa que só o Claude Code a executa. Não verificado: comportamento no Windows e no Cursor de verdade; testado só com git no Linux.

## Agentes
| Agente | Modelo | Quando |
|---|---|---|
| `planner` | Opus | tarefa complexa, antes de codar |
| `implementer-sonnet` | Sonnet | exploração grande que encheria o contexto |
| `implementer-haiku` | Haiku | mesma mudança mecânica em muitos arquivos |
| `reviewer` / `reviewer-senior` | Haiku / Opus | revisão de mudança não trivial (só diff + regras) |
| `quick-decider` | Haiku | dúvida de uma frase |
| `auditor` | Haiku 5.5 (1M nativo) | confere instruções do projeto contra o código e propõe o que mudar (só leitura) |
| `jev-judge` | Haiku | triagem de baixo risco por probabilidades (chave de ambiente) |
| `creative` | Sonnet | imagem e vídeo pela Higgsfield (chave de ambiente, gasta crédito) |

## Chaves (variáveis de ambiente)
| Variável | Para quê | Observação |
|---|---|---|
| `JEV_API_KEY` | `jev-judge` | chave do Workers AI (o Jev estruturado só existe lá) |
| `CLOUDFLARE_ACCOUNT_ID` | Workers AI | id da conta Cloudflare, necessário para o Jev |
| `HIGGSFIELD_API_KEY` | `creative` | cada geração gasta crédito e só roda com aprovação do usuário |

Para trocar o modelo ou a URL: `JEV_PROVIDER` (só `workers-ai`), `JEV_BASE_URL`, `JEV_MODEL`. Para conferir sem gastar: `bash bin/kuru ask-jev --dry-run`.

**No Claude Code na nuvem**: menu do ambiente na barra de título da sessão → *Edit* → *Network secrets* (ou variável de ambiente, se a seção não aparecer). Uma sessão nova já enxerga. Nunca cole uma chave no chat. Em *Network access*, libere `api.cloudflare.com` e `api.higgsfield.ai`.

## Usar
Este repositório é o **harness**, não um projeto que o usa: ele existe para ser instalado **uma vez, globalmente**, e valer em todos os seus projetos. Nunca se copia para dentro de outro projeto.

- **Instalar ou atualizar:** `git pull` neste clone e `bash bin/kuru install --global` (`--dry-run` mostra antes). Rodar de novo só reescreve o que mudou. Não há atualização automática, de propósito. Depois da primeira instalação, basta pedir ao Claude "atualiza o kuru": a skill `atualizar-kuru` acha o clone (guardado em `~/.claude/kuru/.manifest.json`), faz o pull e roda a instalação. Na primeira vez, peça: "Clone https://github.com/AthosMontarroyos/KuruHarness em ~/KuruHarness e rode `bash bin/kuru install --global`".
- **O que a instalação faz:** copia o kit para `~/.claude/kuru`, os agents para `~/.claude/agents` e a skill para `~/.claude/skills`; troca `bash bin/kuru` pelo caminho global; junta a política de delegação no `~/.claude/CLAUDE.md` (entre `kuru:begin/end`, uns 4 mil caracteres que custam tokens em todo projeto) e o hook e as permissões no `~/.claude/settings.json`, guardando `.kuru-bak` do que existia. Arquivo seu com o mesmo nome não é sobrescrito sem `--force`. O hook de fim de tarefa confere só o diff do projeto, não o repositório inteiro.
- **Windows:** os comandos rodam no Git Bash (o Claude Code usa ele para o Bash e para os hooks). Para a instalação manual, abra o **Git Bash**: no PowerShell, `bash` pode ser o do WSL, que é outro ambiente. Se preferir o PowerShell, `py harness/cli.py install --global` faz o mesmo sem passar pelo bash. O hook global usa `"shell": "bash"`.
- **Na nuvem:** o `~/.claude` do ambiente é outro. Rode a instalação no script de setup do ambiente (clone deste repositório e `bash bin/kuru install --global`).
- **Desfazer:** apague `~/.claude/kuru`, os agents e skills listados em `~/.claude/kuru/.manifest.json`, o bloco entre os marcadores e a entrada do hook.

Requisitos: Python 3 (o `bin/kuru` testa `python3`, `python` e `py` e ignora o atalho quebrado da Microsoft Store no Windows) e Git; sem Python o `bin/kuru` sai com 127; comando desconhecido ou sem argumento sai com 2. No Windows, o Claude Code roda os comandos pelo Git Bash.

## Mapa
`.claude/agents/` e `.claude/skills/` (o kit), `.claude/settings.json` (hook e permissões), `harness/` e `bin/kuru` (roteador, briefing, revisão, regras, worktree isolado, log de tarefas `tasklog`, chamadas de API), `scripts/` (hook de fim de tarefa), `CLAUDE.md`/`SPEC.md`/`TASKS.md` (regras, especificação e ledger), `tests/` (`python -m unittest discover -s tests -t .`).

Já foi plugin (PR #5) e saiu: exigia prefixo em tudo e não carregava o `CLAUDE.md`. Está no histórico do git.
