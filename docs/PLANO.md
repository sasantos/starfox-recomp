# Plano do port

O primeiro marco jogável é completar uma missão solo da versão base no Windows x64, com imagem, controle, áudio e progresso persistido. O objetivo do projeto é cobrir toda a campanha offline. O pacote de atualização terá um perfil separado depois de estabilizar a base.

## Fases e critérios de saída

| Fase | Estado | Trabalho | Critério de saída |
| --- | --- | --- | --- |
| **0 · Dump e ambiente** | Concluída | Verificar o NUP, identificar os perfis, separar ExeFS e RomFS e levantar o ambiente host. | Verificação completa passa, inventário reproduzível e ExeFS base extraído com hashes conferidos. |
| **1 · Recompilação da CPU** | Executável de diagnóstico passa no autoteste | Mapear os módulos e imports. Adaptar o lifter ARM64 e o linker ao layout base e ao `TLSDESC`. Gerar C em blocos, compilar e ligar com Clang. | Um executável Windows x64 reproduzível, com instruções e relocações usadas cobertas e testes diferenciais para semântica nova. |
| **2 · Boot do jogo** | Concluída na base | Adaptar o host Horizon para memória, threads, TLS, SVC, IPC e filesystem. Montar o RomFS no perfil correto e oferecer leitura aleatória de `data.zip` como VZIP original. | Entrypoint e inicializadores executam. O jogo lê o cabeçalho VZIP e chega ao primeiro `nvnBootstrapLoader`. [Resultados](FASE-2.md) |
| **3 · NVN 2 sem renderização** | Concluída na base | Mapear a tabela de procedimentos do SDK do Star Fox e registrar comandos com um backend nulo. Medir o caminho de apresentação e os retornos de sincronização. | `--probe-nvn-boot` registra oito envios concluídos com comandos e apresentações consecutivas. [Resultados](FASE-3.md) |
| **4 · Shaders e primeiros quadros** | Concluída na base | Capturar shaders do menu e da missão inicial. Traduzir Ampere para SPIR-V com a cadeia de referência e reproduzir texturas, pipelines e sincronização em Vulkan. | Shaders Ampere traduzidos, pipeline Vulkan 1.4 operacional no Windows x64 / RTX 5090, 8 submits e 6 presents com apresentação em swapchain 4K e captura de quadro. [Resultados](FASE-4.md) |
| **5 · Primeira missão jogável** | Em andamento | Integrar controle, áudio, vídeos e saves. Resolver falhas de GPU e medir desempenho com caches frio e quente. | Iniciar, jogar e concluir uma missão. Fechar o processo, reabrir e carregar o progresso. Registrar GPU, driver e resultado. |
| **6 · Campanha e distribuição do código** | Pendente | Cobrir rotas da campanha, testar uma matriz de GPUs e automatizar o build local. Avaliar separadamente a atualização `0x20000`. | Campanha base concluída e build reproduzido a partir de um checkout limpo e do dump do usuário. Código de terceiros adotado com licenças e avisos preservados. |

## Próxima entrega da Fase 5

1. Configuração e mapeamento de Input (`nn::hid` Joy-Con / Pro Controller para teclado e gamepad host XInput/SDL2).
2. Integração de subsistema de Áudio (Wwise 2024.1, streams Opus e saída para dispositivo de áudio host).
3. Avançar a execução do motor gráfico além do carregamento de pacotes do menu inicial (`title_screen_ftf.level.package_list`) e prólogo cinematográfico.
4. Reprodução contínua da cena e validação de persistência de savegames (`save:/save_game_data.save`).

## Decisões de integração

- Começar pelo **pacote base** fixa um único layout de código e dados. A atualização troca o `main`, o `main.npdm` e o contêiner VZIP. Cada execução deve combinar código e RomFS do mesmo perfil.
- Avaliar o **lifter e o pipeline de build do Ocarina** primeiro. A leitura do NSO já funcionou e o layout upstream admite vários `subsdk`. Os arquivos de patches, endereços, hashes, listas de shaders e configuração dos jogos de referência são específicos das respectivas versões.
- Usar os marcos **CPU → Horizon → NVN 2 → shaders → Vulkan** de Bananza. Confirmar câmera, CUDA e DLSS em traces reais. Se algum estiver no caminho crítico, implementar a menor interface funcional que preserve os contratos do jogo. Medir quais recursos Vulkan a primeira cena de fato usa antes de definir requisitos gerais de GPU.
- Testar o **VZIP com o leitor do próprio jogo** sobre uma visão de RomFS com leitura aleatória e offsets de 64 bits. Um leitor VZIP no host entra no plano se o boot ou a preparação de shaders exigir acesso direto ao índice interno.

## Revisões de referência

- **Ocarina Recomp** (`main`, `a12af268d7474b0d63a903d3a27bf1c487d0ecbe`). Leitura NSO, tradução ARM64 para C e fluxo de build local. [Revisão consultada](https://github.com/sostenesfreitas/ocarina-recomp/tree/a12af268d7474b0d63a903d3a27bf1c487d0ecbe)
- **DKB PC Recomp** (`bananza`, `78eb64907c39942aa99055e787ccecc753b44a9b`). Separação dos marcos do host Horizon, NVN 2, shaders e Vulkan. [Plano na revisão consultada](https://github.com/sasantos/dkb-pc-recomp/blob/78eb64907c39942aa99055e787ccecc753b44a9b/docs/bananza-plan.md)
- **NUP** (`a4840f06c94ddeb414eea5b33c9704ffe995f11c`). Leitor, especificação e verificação do contêiner. [Especificação na revisão usada](https://github.com/a55uka/nup/blob/a4840f06c94ddeb414eea5b33c9704ffe995f11c/SPEC.md)
