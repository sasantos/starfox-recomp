# Fase 3 · NVN 2 sem renderização

O Star Fox base `0x0` criou o dispositivo NVN, carregou recursos do VZIP e avançou pelo loop gráfico. A sonda `--probe-nvn-boot` exige pelo menos oito envios concluídos com comandos e três apresentações no backend nulo. A execução em perfil local de validação concluiu **oito envios e seis apresentações**, com código 0.

| Observação | Resultado |
| --- | --- |
| Consultas ao loader NVN | 731 nomes distintos, dos quais 698 estão registrados e 33 usam o stub diagnóstico de nomes ausentes. A presença na tabela inclui stubs nomeados. |
| Envios | O primeiro envio tinha um handle. Um envio no início do loop tinha 13, e os cinco seguintes tinham 11 handles cada na execução registrada. |
| Sincronização | `nvnCommandBufferFenceSync` registra o destino no buffer de comandos. A fila publica a fence do lote antes de voltar ao jogo. A sonda unitária verifica que `nvnSyncWait` sinaliza a fence gravada no backend nulo. |
| Apresentação | `nvnQueuePresentTexture` avançou o contador da camada. `nn::vi::GetLatestFrameNumber` lê esse contador. |
| CPU | O lifter agora traduz as 71 ocorrências de `UDOT` vetorial. O teste diferencial passou em 500 casos com Unicorn MAX, incluindo as formas de 64 e 128 bits, operandos sobrepostos e overflow do acumulador. Restam 76 ocorrências sem tradução fora do trecho exercitado. [Referência de instruções da Arm](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab) |

## Decisões de integração

- O runtime passa a opção original `-os_fibers` pelas funções de argumentos do SDK. Cada fibra usa o contexto e a pilha do host já previstos pelo kernel da referência. O runtime preenche os campos que o motor lê para reconhecer suas fibras e que o SDK usa para diagnosticar a pilha ativa.
- Os pares TCP IPv4 usados para acordar tarefas têm portas e filas em memória. Cada conexão só alcança um listener do próprio processo. O diagnóstico também usa a entropia do Windows, um controle local e filas vazias para convites e compras. [ABI BSD no libnx](https://github.com/switchbrew/libnx/blob/master/nx/source/services/bsd.c)
- A interface do gerenciador Opus usa `libopus` e mantém a fila de pedidos do SDK. A saída virtual de áudio funciona como um destino silencioso com capacidade e consumo de frames medidos pelo relógio. A fase cobre a inicialização desses serviços durante o boot. [Referência de áudio do nxnative](https://github.com/seedds/nxnative/blob/b2d46b86d03f4b03afe11ea61c67cdf00d7a5345/docs/reference/audio.md#sdk-21s-outputstream-on-a-virtual-output-device)
- O tamanho de reserva de ZCull é uma aproximação alinhada ao alvo de profundidade. O backend nulo contabiliza apresentações e preserva os efeitos de sincronização necessários ao loop. DLSS e a saída de imagem ficam para a validação Vulkan. [Implementação NVN do nxnative](https://github.com/seedds/nxnative/blob/b2d46b86d03f4b03afe11ea61c67cdf00d7a5345/dm/gfx/nvn/hle_nvn.c)

## Reproduzir

Use o RomFS e o ambiente preparados na [Fase 2](FASE-2.md). Gere o C de novo para aplicar a tradução de `UDOT`. O script verifica a versão do lifter antes de reutilizar o C gerado.

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py .\tools\phase1.py generate --jobs 12
& $py .\tools\phase1.py build --jobs 12

$env:PATH = 'C:\msys64\ucrt64\bin;' + $env:PATH
$env:TOTK_INPUT = 'none'
$env:TOTK_AUDIO = 'none'
$env:TOTK_TRACE = 'gfx,present,fs,ipc'
& .\build\phase1-base\ocarina.exe --probe-nvn-boot --profile .\build\phase3-validation-profile *> .\build\phase3-nvn.log
$bootExit = $LASTEXITCODE
Get-Content .\build\phase3-nvn.log -Tail 5
$bootExit
```

A sonda escolhe o backend nulo e só retorna sucesso após os checkpoints. `TOTK_TRACE` registra os nomes consultados, as leituras do arquivo, a abertura das conexões locais e as apresentações. Para testar os objetos e efeitos NVN isoladamente, execute `ocarina.exe --probe-nvn`.

Na compilação verificada, `--selftest`, `--boot` e `--probe-nvn` também passaram. A sonda NVN isolada cobriu 975 verificações, entre elas a fence gravada e 48 tipos de comandos. As apresentações da Fase 3 contabilizam o caminho do jogo até a fila. O primeiro quadro com imagem e a validação do caminho Vulkan continuam na Fase 4.
