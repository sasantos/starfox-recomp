# Diagnóstico inicial

## Conteúdo verificado

O contêiner NUP v1 tem **30.154.808.829 bytes** (28,08 GiB), seis diretórios e vinte entradas de arquivo. A verificação estrutural e a recomputação de todos os SHA-256 passaram com `nup verify`. O inventário completo da tabela está em `build/inventario.json`.

| Pacote | Revisão bruta | Build ID de `main` | `romfs/data.zip` |
| --- | --- | --- | ---: |
| 0, base | `0x0` | `898024ffa42c059518eb38196f1ee0f635ecdf89` | 14.381.483.706 bytes |
| 1, atualização | `0x20000` | `a7730d0f74d168d90422354c8317f76ff78ad938` | 15.611.573.424 bytes |

- O Title ID nos dois registros é `0400E88025B1A000`. A versão comercial não consta nos metadados lidos. Use a revisão bruta e o SHA-256 de `main` para distinguir os perfis de build.
- Cada ExeFS tem `main`, `main.npdm`, `rtld`, `sdk` e `subsdk0` a `subsdk3`. Os oito arquivos de cada pacote foram extraídos separadamente e verificados. `main` e `main.npdm` diferem entre os dois pacotes. Os seis NSO restantes têm hashes iguais.
- O RomFS de cada pacote tem `data.zip` e `veclipse_build.cvar`. O arquivo de dados começa com `VZIP` nos dois pacotes. A estrutura interna e as operações que o jogo faz nesse arquivo ainda precisam ser mapeadas. A primeira tentativa de montagem deve oferecer o arquivo original ao jogo e observar as leituras, antes de decidir se o host precisa interpretar VZIP.
- O comando `nup info` da referência falha ao decodificar um campo de metadados localizado desse dump. `nup verify` e o leitor usado por `tools/dump.py` funcionaram. O inventário lê a tabela de conteúdo sem depender desse campo.

## Leitura preliminar dos NSO da base

O leitor `recomp/nso.py` do Ocarina abriu os sete NSO diretamente do ExeFS, descomprimiu os segmentos com LZ4 e leu `MOD0`, símbolos e relocações. O `main` tem 186.823.296 bytes de código após descompressão. A sonda com `unzbic` retornou `Unknown frame descriptor`. A extração do NUP usa zstd no contêiner e a leitura do NSO usa LZ4 nos segmentos internos.

`main` declara via `DT_NEEDED` `nnSdk.nss`, `multimedia_compat_nx.nss`, `camera.nss`, `dlss.nss` e `cuda.nss`. A presença dessas dependências define o que investigar no linker. A necessidade de cada serviço para chegar ao menu e jogar uma missão será determinada por execução instrumentada.

`subsdk2` contém uma relocação AArch64 do tipo `1031` (`TLSDESC`). Verificar como o linker de referência resolve o descritor TLS e como o runtime reserva o armazenamento por thread. O `rtld` fica no inventário para comparar a inicialização com a do loader no Windows. [ABI AArch64 da Arm](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst#dynamic-relocations)

## Máquina de referência

Windows 11 Pro x64, cerca de 64 GiB de RAM e GeForce RTX 5090. `vulkaninfo` reportou Vulkan 1.4 no dispositivo, com `VK_EXT_mesh_shader`, `taskShader` e `meshShader`. Python 3.12, Clang 22.1, CMake 3.31, Ninja 1.13 e .NET SDK 10 estavam disponíveis. A Fase 1 precisa validar a compilação e a linkedição com o toolchain escolhido para o runtime.
