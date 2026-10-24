# CLAUDE.md — KuruHarness

Kit de subagents do Claude Code. Fases e critérios: `SPEC.md`. Estado: `TASKS.md`.
**Você decide sozinho quando delegar; nenhum comando é necessário.** O procedimento detalhado está na skill `delegar` (só carrega quando você precisar).

## Escopo
O kit mora em `.claude/` (agents e skills), `harness/`, `bin/kuru` (launcher que acha o Python, também no Windows) e `scripts/`. Não é plugin: plugin exige prefixo em tudo e não carrega este arquivo. Fora do escopo: o agente pessoal do usuário e a migração dele para a Cloudflare.

## Regras gerais
- Só avance de fase quando o critério de pronto passar; registre o resultado em `TASKS.md`.
- Máximo de 3 tentativas por tarefa; na terceira falha, pare e reporte. Não tente uma quarta.
- Chaves e tokens só em variável de ambiente, nunca em arquivo.
- Commits coesos por intenção, em português, sem push forçado nem reescrita de histórico.
- Teto de US$ 5/mês em DeepSeek e Higgsfield (chamada direta por API: o limite é o saldo pré-pago e a aprovação do usuário). Jev sem teto, mas sem loops.
- Agentes em paralelo: de 3 a 5 (Cursor: no máximo 3).

## Autonomia: quando delegar
Delegar custa tokens (prompt do agente, briefing e resposta). Só compensa se poupar o seu contexto ou melhorar a qualidade.
**Faça você mesmo, sem agente:** tarefa trivial (1 arquivo, mudança pequena, baixo risco), o que já está no seu contexto, perguntas, texto e ajustes pequenos.
**Delegue quando:**
- for ler ou explorar mais de 6 arquivos, logs ou diffs grandes: `implementer-sonnet` (poupa o seu contexto);
- for a mesma mudança mecânica repetida em muitos arquivos, sem decisão: `implementer-haiku`;
- a tarefa for complexa ou de arquitetura (multi-arquivo): `planner` antes de codar;
- a tarefa for longa (8+ arquivos, reescrita): Cursor, com briefing (seção abaixo);
- precisar de revisão independente de mudança NÃO trivial: `reviewer` (contexto limpo);
- for decisão fechada de baixo risco: `jev-judge`; imagem ou vídeo: `creative`; reserva barata de texto: `deepseek-coder`.
Em dúvida sobre o tamanho: `bash bin/kuru route "<tarefa>" --files ...` (grátis, sem modelo).
**Isolamento:** todo agente começa SEM contexto. Dê só um briefing autocontido (`bash bin/kuru brief ...`), nunca a conversa, e peça resposta curta (até 15 linhas). Cada agente já carrega o que precisa na própria definição.
**Revisão:** mudança trivial: `bash bin/kuru check-rules` basta (o hook de fim de tarefa também roda). Não trivial: fluxo de 3 estágios da skill `delegar`; o revisor recebe só diff + regras relevantes.

## Cursor (não lê este arquivo)
O Cursor NÃO recebe o `CLAUDE.md` nem nenhuma instrução do projeto: tudo vai escrito no prompt. Gere sempre com `bash bin/kuru brief --task ... --files ... --criteria ... --tests ... --out .kuru/cursor/<id>.prompt`; o `bash bin/kuru cursor-task` recusa prompt sem as regras. Modelo fixo `grok-4.7-high-fast`. Se o Cursor estiver indisponível (sem saldo, deslogado, CLI ausente): DeepSeek (tarefa sem risco alto) e depois Sonnet. Aplique o diff só depois de revisar.

## Provedores e chaves
Variáveis de ambiente: `DEEPSEEK_API_KEY` (DeepSeek, OpenRouter `sk-or-` ou Workers AI com `CLOUDFLARE_ACCOUNT_ID`), `JEV_API_KEY` (Workers AI), `HIGGSFIELD_API_KEY` (só gera com `--yes` e com a aprovação do usuário), `CURSOR_API_KEY`. Conferir sem gastar: `bash bin/kuru ask-deepseek --dry-run`. O Jev erra com confiança alta (87,5% de acerto contra 97,5% do Haiku): é indício, nunca prova, e não serve de porteiro de diffs. Os formatos completos estão nas definições de `jev-judge`, `creative` e `deepseek-coder` e em `bash bin/kuru ask-jev --example`.

## Regras para quem codifica (entram por extenso no briefing de qualquer agente, inclusive o Cursor)
- Siga o estilo do código ao redor: nomes, idioma e densidade de comentários do arquivo. Comentários, mensagens e documentação em português, a menos que o arquivo já use outro idioma.
- Faça a menor mudança que cumpre a tarefa. Não refatore nem renomeie o que não foi pedido.
- Se o projeto tem testes, escreva ou atualize os testes junto e rode a suíte antes de terminar.
- Todo arquivo em `.claude/agents/` declara `model` no frontmatter.
- Em `TASKS.md`, só marque `[x]` com o comando e o resultado na mesma linha.
- O limite de 3 tentativas por tarefa não pode ser aumentado nem removido, em código, hook ou documentação.
- Arquivos de trabalho temporários vão em `.kuru/` (ignorada pelo git), nunca em `.claude/`, que o Claude Code protege.
- Nunca grave chaves, tokens ou senhas em arquivo.
