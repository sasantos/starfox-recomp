# Fase 4 · Shaders e primeiros quadros

O Star Fox base `0x0` compilou e vinculou os shaders Ampere do jogo via Vulkan 1.4 no Windows x64 com a GPU host (NVIDIA GeForce RTX 5090). A sonda `--probe-vulkan-boot` concluiu **oito envios NVN, seis apresentações no swapchain 4K (3840x2160) e mais de 105.000 chamadas NVN** sem erros de validação, encerrando com código 0 e salvando o primeiro quadro capturado em `build/first-frame.png`.

| Checkpoint | Resultado |
| --- | --- |
| Tradutor de Shaders | Binário NativeAOT `totk_xlate.exe` (ID `54852000545921d9`) compilado via .NET SDK 10 e integrado em `build/xlate/`. |
| Lowering Ampere → Maxwell | 91 shaders distintos foram inspecionados. 90 compilaram diretamente. O shader `aab96d86af01bb40` requereu implementação do opcode `0x21a` (`SGXT Rd, Ra, Rb`) no Eglantine, rebaixado para `SHL 8` + `BFE.R` (`0x5c00000000000000ULL`). |
| Vulkan Backend | Swapchain 3840x2160 criado na NVIDIA GeForce RTX 5090 (driver 621.14, Vulkan 1.4.357). Graphics Pipeline Library (GPL), decodificador de texturas ASTC compute e pools de memória inicializados. |
| Stubs de Serviços | Implementados 31 stubs para o subsistema `nn::chat` em `refs/ocarina/runtime/ov_system.c` exigidos durante o carregamento de pacotes do menu inicial (`title_screen_ftf.level.package_list`). |
| Execução e Apresentação | 8 envios com até 13 handles, 6 quadros apresentados, 12 render passes, 12 draws e 1 compute dispatch por quadro. Saída com código 0. |

## Decisões de integração

- **Lowering de `SGXT` (Opcode `0x21a`):** O opcode Ampere `0x21a` realiza extração de campo de bits de registro com sinal. No Maxwell (`BFE.R`), o operando `srcB` empacota a posição nos bits 0..7 e o tamanho nos bits 8..15. Como a semântica de `SGXT` já fornece esses parâmetros nos registros de origem, a emissão desloca `srcB` em 8 bits para o registrador scratch 250 (`SHL R250, Rb, 8`) antes de emitir a instrução `BFE.R`. A contagem de escrita (`write_count`) foi atualizada para rastrear `0x21a` e `0x81a`.
- **Stubs `nn::chat`:** O motor Eclipse do Star Fox invoca consultas de sala e sessão de bate-papo de voz durante o carregamento do pacote de menu. Sem esses stubs, a aplicação tenta acessar um ponteiro de sessão nulo gerando violação de acesso (`0xc0000005`). Os stubs foram derivados da especificação de serviços do Horizon e do `nxnative`, retornando ausência de sala/sessão ativa e permitindo que o carregamento prossiga normalmente.
- **Sonda `--probe-vulkan-boot`:** Adicionada ao `main.c` para automatizar a validação do pipeline gráfico Vulkan sob o perfil de boot do Star Fox, com suporte a captura de imagem via `--shot <caminho.png>`.
- **Patch cumulativo:** Todas as alterações no runtime e no compilador de shaders foram consolidadas em `patches/phase4-shaders.patch` e registradas em `tools/phase1.py`.

## Reproduzir

Certifique-se de que o tradutor `totk_xlate.exe` está presente em `build/xlate/` e que o binário foi recompilado:

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py .\tools\phase1.py build --jobs 12

$env:PATH = 'C:\msys64\ucrt64\bin;' + $env:PATH
$env:TOTK_INPUT = 'none'
$env:TOTK_AUDIO = 'none'
$env:TOTK_TRACE = 'gfx,present,fs,ipc'
$env:TOTK_XLATE = (Resolve-Path .\build\xlate\totk_xlate.exe).Path
& .\build\phase1-base\starfox.exe --probe-vulkan-boot --profile .\build\phase3-validation-profile --shot .\build\first-frame.png *> .\build\phase4-vulkan-boot.log
$bootExit = $LASTEXITCODE
Get-Content .\build\phase4-vulkan-boot.log -Tail 15
$bootExit
```

A execução registrará a criação do dispositivo Vulkan, a tradução dos shaders, o início do loop gráfico com múltiplos dispatches de compute e renderização, gravando o frame no destino especificado.

Com a validação dos shaders e do backend Vulkan concluída, o projeto avança para a **Fase 5 · Primeira missão jogável**, integrando entrada de controle, áudio Wwise/Opus, reprodução de vídeo e progressão de jogo.

## Correção da fidelidade das LUTs

A investigação dos frames 1, 600 e 3150 mostrou que os computes `8x8x8` do boot geram corretamente as LUTs 3D `64³` usadas pelo color grading. Uma escrita posterior das páginas antigas da CPU podia, porém, reenviar zeros por cima desses dados. O fallback de LUT identidade tornava a cena acinzentada e removia detalhes; a referência executada no Lichii confirmou as cores e o enquadramento esperados.

`vk_texture_storage_bound_locked` agora trata o binding de storage como uma escrita potencial e compartilha com renders/cópias a marcação de conteúdo GPU-owned em `vk_texture.c`. Assim, a imagem produzida pela GPU não é substituída por uma versão antiga do storage. O fallback inicial de identidade continua existindo, mas não substitui mais a LUT gerada durante o boot.

A regressão foi coberta em `--probe-vkcopy-astc`: depois de uma escrita por storage, uma geração antiga de escrita do guest não pode causar outro upload. O teste falhava com `owned 0, uploads 1 -> 2` antes da correção e passa após ela. A sequência da missão terminou sem erros de validação, shaders falhos ou draws perdidos. A tela inicial e as nuvens foram comparadas com a referência; as transmissões posteriores ainda exigem investigação de exposição e iluminação.

A apresentação real também foi verificada separadamente do dump. O `totk.ini` local tinha um preset customizado que clareava novamente a imagem corrigida. O preset foi restaurado para `default`, com brilho `0`, contraste e saturação `100` e gamma `1`, corrigindo a tela inicial. Esses ajustes não resolvem o escurecimento excessivo observado em algumas cenas posteriores.

## Correção do volume de luz (compute NVN 2)

O escurecimento das cenas internas vinha, em parte, do compute que monta o volume 3D de luz (`88x50x50 rgba16f`, dispatch `22x13x13`, frames 872 a 1042 da sequência do cockpit). A imagem que ele escreve e as três texturas de sombra que ele lê caíam em descritores dummy. Assim, o shader de iluminação seguinte lia um volume antigo, e o feixe volumétrico da plataforma não aparecia.

O banco c0 do NVN 2 tem duas tabelas que o runtime não conhecia, entre as texturas e as imagens: texturas separadas (controle `+0xb4`) e samplers separados (`+0xb5`). Nesse compute, as contagens são 13 uniform buffers, 4 texturas em `0xe0`, 32 texturas separadas em `0x100`, 13 samplers em `0x200` e 5 imagens em `0x268`. O tamanho do banco informado pelo driver em `+0xba` (`0x290`) bate com essa ordem nos 11 computes registrados. Sem as duas tabelas, o handle da imagem (`0x288`, slot 4) ficava fora da faixa. O tradutor, além disso, declarava essa imagem como `R8G8B8A8Unorm`.

- `nvn2_lower.cpp` copia `+0xb4/+0xb5` para o bloco DKC1 (`+20`) e confere o total contra `+0xba`.
- `nvn2_c0.h` inclui as tabelas no layout (partes 6 e 7). Sem elas, o layout continua idêntico ao anterior.
- O pedido ao tradutor ganha o campo opcional `c0_separate`, enviado só quando não é zero. Por isso as chaves de cache dos demais shaders não mudam. O tradutor (`tools/xlate/Program.cs`) usa o campo para tipos e formatos, devolve-o no `.res.json` e o `--probe-nvn2-c0` cobre o layout do Star Fox.
- `gfx_shader.c` mapeia as texturas separadas para o slot vinculado e o sampler (metade alta do handle) para o slot de sampler correspondente.

Com o tradutor `29fba628df735893`, o dump do frame 950 mostra a imagem de saída em `t346 88x50x50 rgba16f`, as sombras `8192x8192 d16` e `8192x4096 d32f` vinculadas e nenhum descritor dummy no frame. A cena passa a mostrar o feixe azul da referência do Lichii. As três grades de luz `r32ui` lidas por esse passe continuam zeradas; ainda falta descobrir se a cena não tem luzes locais ou se o compute anterior não as escreve.
