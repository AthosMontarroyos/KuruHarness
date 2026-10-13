# KuruHarness

Projeto em fase inicial, desenvolvido passo a passo.

## Compatibilidade planejada

O projeto terá dois harnesses de compatibilidade:

- **Cursor** — harness para integração com o Cursor.
- **Codex** — harness para integração com o Codex.

O suporte aos dois harnesses faz parte do escopo inicial. Os detalhes de arquitetura e implementação serão definidos nas próximas etapas.

## Arquitetura de UI

O código da aplicação é a fonte principal da UI. Cursor e Codex implementam diretamente nas páginas, rotas e componentes reais, usando o contexto, as referências e as skills fornecidos pelo usuário. O sitemap orienta a estrutura e a navegação quando necessário; o Impeccable orienta a qualidade visual durante a implementação.

O fluxo é: **contexto + sitemap + referências + skills → implementação → validação na aplicação → ajustes no código**. O usuário avalia a UI funcionando, sem uma etapa prévia obrigatória de design nem um HTML separado para aprovação. Não há dependência do Figma ou de outro editor de design.

As regras de implementação e validação compartilhadas pelos dois harnesses estão em [skills/design/SKILL.md](skills/design/SKILL.md).
