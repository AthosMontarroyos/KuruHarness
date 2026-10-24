# KuruHarness

Kit de subagents para o **Claude Code**: roteia cada tarefa pelo tamanho, implementa com o modelo certo, revisa o diff em 3 estágios e registra o resultado.

## Como usar

Abra o Claude Code **dentro deste repositório**. Tudo vale sem instalar nada: subagents e comandos (`/task`, `/review`) ficam em `.claude/`, o `CLAUDE.md` carrega sozinho e o hook de fim de tarefa vem de `.claude/settings.json`. Os subagents de API (`deepseek-coder`, `jev-judge`, `creative`) funcionam **sem comandos, sem plugin e sem MCP**: basta a chave no ambiente.

Para levar o kit a outro projeto, copie `.claude/agents/`, `.claude/commands/`, `harness/`, `bin/` e `scripts/`, e junte as regras do `CLAUDE.md` e o bloco `hooks`/`permissions` do `.claude/settings.json` aos seus. Os comandos chamam o launcher por `bash bin/kuru`, então `bin/` precisa estar na raiz do projeto.

## Chaves (variáveis de ambiente)

| Variável | Para quê | Observação |
|---|---|---|
| `DEEPSEEK_API_KEY` (ou `DEEP_SEEK_API_KEY`) | agente `deepseek-coder` | chave do DeepSeek, do OpenRouter (`sk-or-...`) ou do Workers AI; o provedor é detectado pelo formato |
| `JEV_API_KEY` | agente `jev-judge` | chave do Workers AI (o Jev estruturado só existe lá) |
| `CLOUDFLARE_ACCOUNT_ID` | Workers AI | necessário quando alguma chave for do Workers AI |
| `HIGGSFIELD_API_KEY` | agente `creative` | geração de imagem e vídeo; cada geração gasta crédito |
| `CURSOR_API_KEY` | `bin/kuru cursor-task` | opcional, para tarefas longas no Cursor |

Opcionais para trocar provedor ou modelo: `DEEPSEEK_PROVIDER` (`deepseek`, `openrouter` ou `workers-ai`), `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `JEV_BASE_URL`, `JEV_MODEL`. Para conferir sem gastar nada: `bash bin/kuru ask-deepseek --dry-run`, `bash bin/kuru ask-jev --dry-run`.

**No Claude Code na nuvem**: abra o menu do ambiente na barra de título da sessão, escolha *Edit* e coloque as chaves em *Network secrets* (ou como variável de ambiente, se essa seção não aparecer). Uma sessão nova já as enxerga. Nunca cole uma chave no chat. Em *Network access*, libere os hosts `api.deepseek.com`, `openrouter.ai`, `api.cloudflare.com` e `api.higgsfield.ai`.

## Requisitos
- Python 3 (o `bin/kuru` testa `python3`, `python` e `py` e ignora o atalho quebrado da Microsoft Store no Windows) e Git. No Windows, o Claude Code roda os comandos pelo Git Bash.
- Opcionais: **Cursor CLI** (`agent`) para tarefas longas, com o modelo fixo em `grok-4.7-high-fast` (o padrão da conta é `auto`; confira com `agent models`); e o servidor MCP `kuru-subagents` (um Worker do usuário), que não faz parte deste repo e do qual nada aqui depende. Sem chave do DeepSeek no ambiente, a cadeia de codificadores pula o DeepSeek e vai ao Sonnet.

## Mapa
- `.claude/agents/`, `.claude/commands/`, `.claude/settings.json`: o kit.
- `harness/`, `scripts/`, `bin/kuru`: roteador, revisão, checagem de regras, log e runner do Cursor.
- `CLAUDE.md`, `SPEC.md`, `TASKS.md`: regras, especificação e ledger.
- `tests/`: `python -m unittest discover -s tests -t .`.

## Por que não é plugin
Foi plugin por um tempo (PR #5) e saiu: todo comando e agent ganhava prefixo, um plugin não carrega o `CLAUDE.md` (e o Claude deixava de saber o formato do Jev) e não traz regras de permissão. Está no histórico do git.
