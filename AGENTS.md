# Instruções do projeto

O KuruHarness terá dois harnesses de compatibilidade: **Cursor** e **Codex**.

## Sincronização das instruções

Ao alterar a arquitetura, os fluxos de trabalho, as skills ou as instruções do projeto, revisar obrigatoriamente [`.codex/config.toml`](.codex/config.toml), especialmente `developer_instructions`, e atualizar as regras afetadas na mesma tarefa. Não considerar a mudança concluída verificando apenas `AGENTS.md`, `README.md` ou as skills.

Conferir a consistência entre esses arquivos e as instruções equivalentes do Cursor, quando existirem. Preservar configurações sem relação com a mudança, como modelo e preferências do aplicativo. Na entrega, informar se o `config.toml` foi atualizado ou revisado sem necessidade de alteração; se a escrita estiver bloqueada, informar a pendência explicitamente.

## Skills do projeto

Ao planejar, criar ou alterar interfaces, ler e seguir [skills/design/SKILL.md](skills/design/SKILL.md).

Essa skill define a implementação da UI diretamente no código da aplicação, orientada pelo contexto, sitemap, referências e skills fornecidos pelo usuário. Cursor e Codex compartilham as mesmas instruções, componentes e tokens no repositório. O usuário valida a aplicação funcionando e os ajustes acontecem no próprio código. Não exigir uma etapa prévia de design, Figma, mockups ou HTML separado para aprovação.
