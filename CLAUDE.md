# CLAUDE.md — regras do projeto KuruHarness

Harness de sub-agents do Claude Code. O plano completo e os critérios de pronto de cada fase estão em `SPEC.md`. O estado vivo das tarefas está em `TASKS.md`.

## Escopo
O kit mora em `.claude/` (subagents e comandos), `harness/`, `bin/kuru` (launcher que acha o Python, também no Windows) e `scripts/`. Não é plugin: um plugin exigia prefixo em tudo (`/review`) e não carrega o `CLAUDE.md`, que é onde o Claude aprende, por exemplo, o formato do Jev.

Este harness é do agente de código (Claude Code). O agente pessoal do usuário, e a futura migração dele para a Cloudflare, é outro projeto e está fora do escopo daqui. Por enquanto o DeepSeek segue como reserva usando o saldo que o usuário já tem lá, com o teto de US$ 5/mês aplicado pelo Worker.

## Regras gerais
- Só avance de fase quando o critério de pronto da fase atual passar. Registre o resultado em `TASKS.md`.
- Máximo de 3 tentativas por tarefa. Na terceira falha, pare e reporte; não tente uma quarta.
- Teto de custo: US$ 5/mês em DeepSeek e em Higgsfield. As chamadas diretas por API (agentes `deepseek-coder` e `creative`) **não passam pelo contador do Worker**: o limite do DeepSeek é o saldo pré-pago do provedor, e o do Higgsfield é a regra de só gerar com a aprovação do usuário (`--yes`). Jev não tem teto (usuário informa que não cobra); ainda assim, evite chamadas em loop.
- Agentes em paralelo: de 3 a 5.
- O revisor recebe só o diff e as regras relevantes, nunca o projeto inteiro.
- Nunca grave tokens, chaves ou segredos no repositório. `MCP_TOKEN` e afins vivem só como secrets do Worker.
- Commits coesos por intenção, em português, sem push forçado nem reescrita de histórico.

## Fluxo de revisão (Fase 2)
Use `/review <task-id>`. Ordem fixa: 1) `bash bin/kuru check-rules` (grátis, sem modelo); 2) `reviewer` (Haiku) recebendo só o pacote `regras relevantes + diff` gerado por `bash bin/kuru review-flow check`; 3) `reviewer-senior` (Opus) somente depois de 2 reprovações do Haiku na mesma tarefa. Toda reprovação (determinística ou de modelo) conta para o limite de 3 tentativas; na 3ª, parar e reportar. Estado em `.claude/state/reviews.json`. A regra 3 é imposta tecnicamente: os revisores têm `tools: []` e `omitClaudeMd: true` (não leem arquivos nem recebem este CLAUDE.md), e o pacote vai inline no prompt, em partes de até 12 mil caracteres divididas por arquivo.

## Cursor CLI (Fase 3)
Coding longo vai para o Cursor: `bash bin/kuru cursor-task` roda `agent -p --trust --force --model grok-4.7-high-fast` (modo agent é o padrão do CLI; `--mode` só aceita plan/ask) num git worktree por tarefa (sessão nova sempre, nunca `--resume`), no máximo 3 em paralelo, e devolve o diff para o `/review` antes de aplicar. O modelo é fixo no script (`CURSOR_MODEL` para trocar) porque o padrão da conta é `auto`, não o Grok 4.7. Se o Cursor estiver indisponível (sem saldo, deslogado, CLI ausente), a tarefa longa desce a cadeia **Cursor → DeepSeek (só texto, tarefa sem risco alto) → Sonnet** (`planner` + `implementer-sonnet`), conforme o campo `cadeia` de `harness.route`. O texto do erro de "sem saldo" do Cursor não foi observado: qualquer falha do `cursor-task.sh` conta como indisponível. Confira os ids com `agent models`. Usar `CURSOR_API_KEY` não evita que o CLI grave a credencial em `~/.config/cursor`: em máquina compartilhada rode `agent logout` depois. `--force` libera comandos sem confirmação, por isso o `--sandbox enabled` por padrão e o worktree isolado.

## Roteamento inicial (proposta; ajustar com os logs da Fase 6)
- Trivial (1 arquivo, baixo risco): Haiku.
- Média: Sonnet.
- Multi-arquivo ou arquitetura: `planner` (Opus). Fable só se o Opus falhar duas vezes.

## Provedores e chaves (sem MCP, sem plugin, sem comandos)
Os agentes chamam as APIs direto, com chaves lidas de **variáveis de ambiente** (nunca em arquivo, nunca coladas no chat). No Claude Code na nuvem, ficam nas configurações do ambiente.
- **`deepseek-coder`** usa `DEEPSEEK_API_KEY` (alias `DEEP_SEEK_API_KEY`). A chave pode ser do DeepSeek, do OpenRouter (`sk-or-...`) ou do Workers AI (exige também `CLOUDFLARE_ACCOUNT_ID`); o provedor é detectado pelo formato e dá para forçar com `DEEPSEEK_PROVIDER`, `DEEPSEEK_BASE_URL` e `DEEPSEEK_MODEL`. Só devolve texto: o Claude Code aplica o diff depois do `/review`. Teste: `bash bin/kuru ask-deepseek --dry-run`.
- **`jev-judge`** usa `JEV_API_KEY` + `CLOUDFLARE_ACCOUNT_ID`. O Jev estruturado (`typesafe/jev`) só existe no Workers AI; o OpenRouter só tem o Jev Router (chat) e não serve. O `kuru ask-jev` valida o formato antes de chamar (`--example` mostra um válido). Medido: 87,5% de acerto contra 97,5% do Haiku, e a confiança NÃO é calibrada (errou com 0,98): é indício, nunca prova, e não serve de porteiro de diffs; use em triagem de baixo risco.
- **`creative`** usa `HIGGSFIELD_API_KEY`. Cada geração gasta crédito: `bash bin/kuru higgsfield run` só envia com `--yes`, e o agente só passa `--yes` com a aprovação explícita do usuário.
- Na nuvem, a rede do ambiente precisa liberar `api.deepseek.com`, `openrouter.ai`, `api.cloudflare.com` e `api.higgsfield.ai`.
- O servidor MCP `kuru-subagents` (Worker) continua existindo, mas nada aqui depende dele.
