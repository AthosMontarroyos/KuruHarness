---
name: atualizar-kuru
description: Instala ou atualiza o KuruHarness (agents, skills e política) na configuração global ~/.claude. Use SÓ quando o usuário pedir para instalar, atualizar ou reinstalar o kuru, o harness ou os agentes. Não use em nenhuma outra tarefa.
---
O harness é global e a fonte dele é um clone do repositório; `~/.claude/kuru` é só a cópia instalada. Atualizar é: puxar o clone e rodar a instalação.

1. **Ache o clone.** Leia `~/.claude/kuru/.manifest.json` e pegue o campo `_origem` (caminho do clone usado na última instalação). Se o arquivo não existir (primeira vez) ou o caminho não existir mais, clone `https://github.com/AthosMontarroyos/KuruHarness.git` em `~/KuruHarness` (ou na pasta que o usuário indicar) e use essa pasta. Chame de `<clone>`.
2. **Puxe.** `git -C <clone> pull --ff-only`. Se falhar (mudança local ou histórico divergente), pare e conte ao usuário; não use reset, stash nem force.
3. **Veja antes.** `bash <clone>/bin/kuru install --global --dry-run` e leia o JSON: `copiados`, `iguais`, `conflitos`.
4. **Instale.** Sem `conflitos`: `bash <clone>/bin/kuru install --global`. Com `conflitos` (arquivo do usuário com o mesmo nome), liste-os e só use `--force` se o usuário confirmar.
5. **Avise em até 4 linhas:** quantos arquivos mudaram, se houve conflito, e que é preciso abrir uma sessão nova do Claude Code para carregar agents e skills novos. Não rode nada além disso.
