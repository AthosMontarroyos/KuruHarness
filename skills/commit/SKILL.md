---
name: commit
description: Analisa as alterações pendentes do projeto e cria commits separados por intenção, distinguindo correções, funcionalidades e refatorações. Usar quando o usuário pedir para organizar e criar commits das alterações.
---

# Commits por intenção

Ao ser acionada para criar commits, analisar todas as alterações pendentes e executar a separação em commits locais coesos. O pedido já autoriza criar esses commits; apresentar a divisão e prosseguir sem exigir confirmação de rotina. Se o usuário pedir apenas análise ou proposta, não alterar o índice nem criar commits. O Codex planeja na cloud e o Cursor implementa; esta skill usa Git e não depende de ferramentas exclusivas de um deles.

## Analisar e agrupar

- Ler as instruções do repositório e verificar `git status`, os diffs staged e unstaged e os arquivos não rastreados relevantes. Incluir adições, exclusões, renomeações e binários na análise. Consultar o histórico recente para identificar convenções de mensagem. Não incluir arquivos ignorados automaticamente.
- Analisar o conteúdo e o propósito das mudanças; a conversa ajuda a entender a intenção, mas o diff determina o que será registrado. O staging existente é parte da análise, não uma fronteira obrigatória entre commits. Registrar seu estado antes de reorganizá-lo, preservando inclusive versões parcialmente preparadas.
- Agrupar por resultado concreto, não por arquivo, pasta ou simplesmente por tipo. Duas correções independentes podem precisar de dois commits `fix`. Uma funcionalidade pode abranger código, testes, documentação e dependências no mesmo commit.
- Distinguir `fix` (corrigir comportamento incorreto), `feat` (adicionar capacidade) e `refactor` (reestruturar sem mudar comportamento). Usar `docs`, `test`, `build`, `ci`, `perf`, `style` ou `chore` quando descrevem melhor a intenção. Testes e documentação de uma funcionalidade ou correção acompanham essa mudança; recebem commit separado quando têm propósito independente.
- Separar correções, funcionalidades e refatorações independentes mesmo quando estão no mesmo arquivo. Evitar classificar um lote inteiro como implementação só porque inclui uma funcionalidade.
- Ordenar os grupos pelas dependências: por exemplo, uma refatoração preparatória antes da funcionalidade que depende dela. Cada commit deve representar um estado coerente, sem referências quebradas a código que só chega depois.
- Não inventar separações artificiais nem forçar vários commits quando existe apenas uma intenção. Se mudanças forem inseparáveis sem reimplementação ou estados inválidos, manter o menor grupo coerente e explicar a dependência. Escolher o tipo pelo resultado principal, descrevendo as mudanças acopladas no corpo.
- Apresentar brevemente os grupos previstos, suas mensagens e a ordem antes de executar.

## Preparar e criar cada commit

1. Preparar somente as mudanças do grupo atual. Usar caminhos explícitos para arquivos inteiros e seleção de hunks ou patches aplicados ao índice para arquivos com intenções diferentes. Não usar `git add .` ou `git add -A` indiscriminadamente.
2. Quando precisar reorganizar o índice existente, preservar previamente seu conteúdo recuperável e não sobrescrever o working tree. Se usar patches, verificar sua aplicação com `git apply --cached --check` antes de aplicá-los. Conferir o resultado real no índice, inclusive exclusões, renomeações e arquivos novos parcialmente preparados. Não simular separação apenas trocando a mensagem de um commit com alterações misturadas.
3. Revisar `git diff --cached` e `git diff --cached --check` antes de cada commit. Confirmar que não entraram mudanças de outros grupos, credenciais, arquivos locais ou artefatos sem relação com o projeto. Arquivos cuja inclusão não está clara devem ficar pendentes, com o motivo informado.
4. Fazer a validação proporcional à mudança e seguir as verificações obrigatórias do projeto. Ao validar um commit intermediário, testar seu conteúdo preparado em ambiente isolado quando necessário: testes no working tree completo não comprovam que o estado intermediário funciona. Informar quando a validação for apenas estática ou não puder ser executada.
5. Criar a mensagem conforme a convenção do repositório; na ausência dela, usar `tipo(escopo): descrição objetiva`, omitindo escopo quando não ajuda. A mensagem descreve somente o conteúdo daquele commit. Usar corpo para explicar motivação ou dependências quando necessário.
6. Após criar o commit, conferir seu conteúdo e o estado restante. Se hooks modificarem arquivos ou o estado mudar durante a execução, reavaliar os diffs antes de continuar. Não contornar hooks, ocultar falhas nem repetir commits às cegas.

## Preservação e conclusão

- Não descartar alterações, usar reset destrutivo, sobrescrever arquivos, fazer stash, reescrever commits existentes ou publicar com push como parte desta skill. Reorganizar apenas o índice necessário à divisão solicitada.
- Se houver conflitos não resolvidos, merge/rebase em andamento ou alteração concorrente que impeça separar com confiança, interromper a criação e explicar o estado encontrado. Preservar os commits já concluídos e as mudanças restantes; não tentar desfazer trabalho automaticamente.
- Se não houver mudanças elegíveis, informar e não criar commits vazios.
- Ao concluir, listar hash curto, mensagem e propósito de cada commit, as validações realizadas e quaisquer alterações pendentes com seus motivos. Não declarar a árvore limpa sem verificar `git status`.
