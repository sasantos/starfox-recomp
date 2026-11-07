# Fase 1 · Recompilação da CPU

## Perfil e módulos

O perfil `config/starfox-base.json` fixa os SHA-256 dos oito arquivos do ExeFS base. `tools/phase1.py` confere os hashes e a revisão do Ocarina antes de usar as ferramentas upstream. A recompilação segue o layout de seis módulos do Ocarina. O `rtld` original é lido no inventário para comparação com o loader host.

| Módulo | Nome dinâmico | Funções geradas | Ocorrências sem tradução |
| --- | --- | ---: | ---: |
| `main` | — | 233.145 | 85 |
| `subsdk0` | `multimedia_compat_nx.nss` | 2.035 | 0 |
| `subsdk1` | `cuda.nss` | 9.972 | 0 |
| `subsdk2` | `dlss.nss` | 2.157 | 0 |
| `subsdk3` | `camera.nss` | 152 | 0 |
| `sdk` | `nnSdk.nss` | 45.972 | 62 |
| **Total** | | **293.433** | **147** |

Todos os cinco nomes `DT_NEEDED` de `main` resolvem para os módulos da tabela. A busca estática pela ordem do loader resolveu todos os imports fortes. Os 39 imports fracos sem definição incluem 37 símbolos Vulkan de `subsdk2`. A utilidade desses caminhos depende da configuração gráfica do jogo e será verificada em execução.

## Resultados de geração e testes

- O gerador produziu 1.320 blocos C e seis tabelas de funções em 132 segundos. Os manifests por módulo registram o volume, os saltos e as ocorrências sem tradução.
- As ocorrências sem tradução são 71 `UDOT`, 58 `PACGA`, 4 `FNEG` vetoriais FP16 e 14 acessos `MRS` ou `MSR` a registradores de desempenho. O gerador emite traps nesses pontos. Os totais refletem o código descoberto estaticamente.
- O teste diferencial upstream comparou o C emitido com Unicorn em 2.400 casos do `main` e 2.398 casos do `sdk`, com zero divergências na amostra. As instruções sem tradução ficam fora dessa cobertura.
- O mapa de memória original sobrepunha o fim do `sdk` à região do kernel. O patch `patches/phase1-module-window.patch` move o kernel para `0x7020000000` e a janela de funções do host para `0x7030000000`. Os endereços do código gerado continuam os mesmos.
- O executável de diagnóstico PE x64 tem 561,8 MiB. `--selftest` passou com zero falhas e conferiu a tabela de despacho para as 293.433 funções, além de heap, memória física, pilha, `QueryMemory` e `GetInfo`.
- No diagnóstico inicial, `--probe-loader` e `--probe-kernel` encerraram com código 70 em `subsdk2+0x962698`, uma relocação `TLSDESC` com índice de símbolo 0 e adendo 0. A [Fase 2](FASE-2.md) confirmou a inicialização pelo SDK recompilado e usa `--boot` para verificá-la. [ABI de descritores TLS da Arm](https://github.com/ARM-software/abi-aa/blob/main/sysvabi64/sysvabi64.rst#tls-descriptor-resolver-functions)

## Reproduzir

Use a raiz do projeto, com o ExeFS base preparado conforme o README. Para compilar, prepare o MSYS2 UCRT64 com Clang, LLD, Ninja e as dependências do runtime. [Guia de compilação do Ocarina na revisão usada](https://github.com/sostenesfreitas/ocarina-recomp/blob/a12af268d7474b0d63a903d3a27bf1c487d0ecbe/docs/compilar-manual.md)

```powershell
$oot = '.\refs\ocarina'
$pin = 'a12af268d7474b0d63a903d3a27bf1c487d0ecbe'
git init $oot
git -C $oot fetch --depth 1 https://github.com/sostenesfreitas/ocarina-recomp.git $pin
git -C $oot switch --detach FETCH_HEAD

$py = '.\.venv\Scripts\python.exe'
& $py -m pip install -r .\tools\requirements-phase1.txt
& $py .\tools\phase1.py inspect | Set-Content -Encoding utf8 .\build\phase1-nso.json
& $py .\tools\phase1.py generate --jobs 12
& $py .\tools\phase1.py build --jobs 16

$env:PATH = 'C:\msys64\ucrt64\bin;' + $env:PATH
$env:TOTK_INPUT = 'none'
$env:TOTK_GPU = 'null'
& .\build\phase1-base\ocarina.exe --selftest
```

O build aplica o patch cumulativo da fase atual ao checkout local ignorado `refs/ocarina` e reutiliza os objetos compilados nas execuções seguintes. O executável mantém o nome `ocarina.exe` do script upstream. O autoteste funciona sem montar o RomFS. A [Fase 3](FASE-3.md) atualiza os resultados de cobertura da CPU.
