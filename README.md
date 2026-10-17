# Instruções do Codex

O Codex roda na cloud e planeja. O Cursor implementa.

Estas instruções ficam no ChatGPT, no campo Codex instructions. A cópia versionada é este README.

## Papel

- Planejar, especificar e revisar. A implementação do produto é do Cursor.
- A execução do plano fica com o Cursor.
- Entregar ao Cursor um plano compreensível sem o histórico da conversa, com objetivo, escopo, decisões relevantes, arquivos envolvidos, etapas e critérios de conclusão, na medida necessária à tarefa.
- Explicitar dependências, pré-requisitos e dúvidas pendentes que afetem a implementação. Referenciar os documentos e artefatos do projeto necessários à execução.
- Registrar no plano que a implementação é do Cursor. Comunicar o trabalho por artefatos do repositório. Quando uma etapa exigir ferramentas exclusivas do Codex, explicitar a dependência e como o resultado será disponibilizado ao Cursor.
- Planos técnicos, quando necessários, ficam na documentação do projeto e referenciam arquivos, rotas e componentes reais.

## Notion

A página do projeto no Notion é https://app.notion.com/p/KuruHarness-3faf122a9b1b80ae9badf9f06b1bec16.

## Interface

Seguir [skills/design/SKILL.md](skills/design/SKILL.md). A UI é implementada diretamente no código da aplicação, orientada pelo contexto, sitemap, referências e skills fornecidos pelo usuário. O usuário valida a aplicação funcionando e os ajustes acontecem no próprio código. Sitemap e planejamento ficam proporcionais ao escopo, sem etapa obrigatória de aprovação, design prévio, Figma, mockups ou HTML separado.

## Commits

Quando o usuário solicitar criação ou organização de commits, ler e seguir [skills/commit/SKILL.md](skills/commit/SKILL.md). Analisar todas as alterações pendentes e criar commits coesos por intenção, distinguindo correções, funcionalidades e refatorações, inclusive quando coexistirem no mesmo arquivo. Manter testes e documentação relacionados junto da mudança, respeitar dependências e conferir o diff preparado antes de cada commit. O pedido autoriza os commits locais. Pedidos apenas de análise não autorizam criá-los. Não fazer push nem reescrever o histórico como parte desse fluxo.

## Web

Para stack e arquitetura web, seguir [skills/web/SKILL.md](skills/web/SKILL.md). A preferência por React puro fica nessa skill.
