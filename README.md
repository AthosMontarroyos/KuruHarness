# KuruHarness

Projeto em fase inicial, desenvolvido passo a passo.

## Notion

A página do projeto no Notion é [KuruHarness](https://app.notion.com/p/KuruHarness-3faf122a9b1b80ae9badf9f06b1bec16). Por enquanto está vazia.

## Compatibilidade planejada

O projeto terá dois harnesses de compatibilidade:

- **Cursor** — harness para integração com o Cursor.
- **Codex** — harness para integração com o Codex.

O suporte aos dois harnesses faz parte do escopo inicial. Os detalhes de arquitetura e implementação serão definidos nas próximas etapas.

## Skill de commit

A skill compartilhada [commit](skills/commit/SKILL.md) analisa as alterações pendentes e cria commits locais separados por intenção: correções (`fix`), funcionalidades (`feat`), refatorações (`refactor`) e outros tipos pertinentes. Mudanças distintas no mesmo arquivo são separadas por trechos; código, testes e documentação da mesma entrega ficam juntos.

Para acioná-la no Cursor ou no Codex, peça: **“Use a skill em skills/commit/SKILL.md para analisar todas as alterações e criar commits separados por intenção.”** A skill confere o conteúdo de cada commit, respeita dependências e informa o que ficou pendente. Não faz push.

## Arquitetura de UI

O código da aplicação é a fonte principal da UI. Cursor e Codex implementam diretamente nas páginas, rotas e componentes reais, usando o contexto, as referências e as skills fornecidos pelo usuário. O sitemap orienta a estrutura e a navegação quando necessário; o Impeccable orienta a qualidade visual durante a implementação.

O fluxo é: **contexto + sitemap + referências + skills → implementação → validação na aplicação → ajustes no código**. O usuário avalia a UI funcionando, sem uma etapa prévia obrigatória de design nem um HTML separado para aprovação. Não há dependência do Figma ou de outro editor de design.

As regras de implementação e validação compartilhadas pelos dois harnesses estão em [skills/design/SKILL.md](skills/design/SKILL.md).
