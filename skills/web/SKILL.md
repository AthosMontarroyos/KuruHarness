---
name: web
description: Orientar escolhas de stack e arquitetura ao planejar, criar ou evoluir sites e aplicações web full stack, seguindo a preferência do usuário por React puro.
---

# Desenvolvimento web

## Preferência de stack

O usuário prefere criar sites e aplicações full stack com **React puro no frontend**, sem Next.js e sem Vue ou frameworks baseados em Vue como escolha padrão.

A razão é preservar o máximo de liberdade para planejar uma arquitetura própria. Evitar adotar por conveniência um framework que determine a organização da aplicação, o roteamento ou a integração entre frontend e backend.

- Em projetos novos, partir de React e selecionar ferramentas de build, roteamento e demais bibliotecas conforme as necessidades. React puro não significa dispensar bibliotecas ou ferramentas de desenvolvimento.
- Planejar o backend e sua integração com o frontend de acordo com o produto. Essa preferência não fixa linguagem, framework de backend, banco de dados, hospedagem ou estrutura de pastas, nem reduz uma entrega full stack a uma interface estática.
- Não introduzir Next.js, Vue ou outro framework que imponha a arquitetura da aplicação como escolha automática. Uma solicitação explícita do usuário pode substituir essa preferência.
- Em projetos existentes, respeitar a stack e o escopo da tarefa; essa preferência não autoriza migrações ou reescritas por conta própria.

## Interface e compatibilidade

Ao implementar ou alterar interfaces, seguir [a skill de design](../design/SKILL.md), trabalhando diretamente no código da aplicação.

Cursor e Codex compartilham estas orientações. Manter esta preferência nesta skill de web, sem duplicá-la nas instruções centrais do projeto.
