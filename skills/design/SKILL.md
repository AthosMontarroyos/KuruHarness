---
name: design
description: Implementar e ajustar interfaces diretamente no código da aplicação, com contexto, sitemap, referências e skills, sem depender de uma etapa prévia de design.
---

# UI diretamente no código

## Princípio

A entrega é a interface funcionando na aplicação. Implementar diretamente nas páginas, rotas e componentes reais; o usuário valida esse resultado e pede ajustes no próprio código. Não exigir design prévio, aprovação de mockups, arquivo Figma ou protótipo HTML separado antes de implementar.

## Fontes e responsabilidades

Para escolhas de stack e arquitetura web, consultar [a skill de web](../web/SKILL.md).

- **Usuário:** fornece objetivos, funcionalidades, conteúdo, restrições, referências e skills; valida a aplicação funcionando. Suas instruções prevalecem sobre padrões das skills.
- **Contexto e sitemap:** orientam páginas, rotas, navegação e fluxos. Reutilizar a estrutura existente; elaborar um sitemap breve apenas quando o escopo justificar. Não exigir um arquivo ou aprovação separados para isso.
- **Skills:** orientam as decisões durante a implementação. Usar Impeccable para qualidade visual e de interação, consultando `impeccable:impeccable` no Codex ou a instalação equivalente no Cursor. Isso não cria uma etapa obrigatória de design anterior ao código.
- **Código:** é a fonte principal da UI, incluindo componentes, tokens, estilos, estados, comportamento e assets utilizados pela aplicação.
- **Cursor e Codex:** seguem estas mesmas instruções e trabalham sobre o mesmo repositório, sem precisar de links ou estado de ferramentas externas para continuar.

## Fluxo

1. Ler a tarefa, as instruções aplicáveis e a implementação existente. Aproveitar conteúdo, componentes e padrões já definidos. Perguntar somente sobre lacunas que impeçam uma implementação adequada; resolver escolhas rotineiras com o contexto disponível.
2. Para novas páginas ou fluxos, organizar brevemente a navegação e o conteúdo com base no sitemap e nas referências disponíveis. Tomar decisões visuais suficientes para começar, sem transformar esse planejamento em uma entrega ou aprovação obrigatória.
3. Implementar a UI diretamente na aplicação, respeitando sua stack e convenções. Reutilizar componentes e tokens, contemplando responsividade, acessibilidade e estados pertinentes, como carregamento, vazio, erro e sucesso.
4. Executar as verificações apropriadas e inspecionar a interface na aplicação, nos viewports relevantes. Corrigir os problemas encontrados em uma rodada agrupada e confirmar o resultado, evitando ciclos de polimento sem necessidade. Se não for possível executar ou inspecionar a aplicação, informar a limitação sem afirmar que a validação ocorreu.
5. Disponibilizar a implementação para o usuário validar na aplicação funcionando, informando como acessá-la e eventuais limitações reais. Aplicar o feedback diretamente no mesmo código, preservando o que já foi aceito.

## Continuidade e economia

- Registrar apenas decisões duráveis necessárias à continuidade, na documentação existente do projeto. Não duplicar em documentos uma especificação já expressa pelos componentes e tokens.
- Não criar pastas de design, planos por tela, versões paralelas em HTML ou espelhos da UI como requisito do fluxo. HTML que faz parte da própria aplicação é implementação normal.
- Referências externas, imagens e designs existentes são insumos opcionais; sua ausência não bloqueia o trabalho. Usar Figma ou produzir um protótipo separado somente quando o usuário pedir explicitamente, sem torná-los dependências das demais tarefas.
- Em uma passagem entre harnesses, indicar arquivos ou rotas alterados, verificações realizadas e pendências relevantes. Não depender do histórico do chat nem de uma ferramenta de design para retomar a implementação.
