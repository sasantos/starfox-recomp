# Fase 2 · Boot do jogo

O executável Windows x64 da revisão base `0x0` passou no `--selftest` e no `--boot`. O boot com `TOTK_GPU=null` chegou ao primeiro `nvnBootstrapLoader` e encerrou com código 0. O mesmo fluxo passou com a verificação integral da imagem RomFS.

| Checkpoint | Resultado |
| --- | --- |
| Entrypoint | O código recompilado entrou em `nn::init::Start`, executou `nnMain` e montou `rom:`. |
| Inicializadores | Os seis `DT_INIT` chegaram ao estado 2, com 3.347 entradas no total. O SDK do jogo instalou um resolvedor TLS válido no descritor de `subsdk2`. |
| VZIP | O leitor do jogo abriu `rom:/data.zip` e leu 12 bytes no offset 0. O diagnóstico verifica a assinatura `VZIP` nesses bytes. |
| NVN | A primeira chamada foi `nvnBootstrapLoader("nvnDeviceGetProcAddress")`, a partir de `main+0xaad3fc0`. |

## Runtime e dados locais

- O loader deixa o `TLSDESC` local de `subsdk2+0x962698` para o `DT_INIT` do SDK recompilado. O boot confere se o descritor recebeu um resolvedor do SDK com entrada na tabela de despacho. [ABI de descritores TLS da Arm](https://github.com/ARM-software/abi-aa/blob/main/sysvabi64/sysvabi64.rst#tls-descriptor-resolver-functions)
- O host aceita mover pilhas reservadas em páginas graváveis dos módulos. A rede offline responde ao registro BSD e retorna indisponibilidade para abertura de sockets. O runtime fornece uma identidade por perfil local, suporta os módulos carregados estaticamente e representa a ausência de amostras do sensor Joy-Con 2 e de notificações do álbum do console.
- `tools/dump.py --pack-romfs` verifica as duas entradas contra os SHA-256 do NUP e grava a imagem de leitura com offsets de 64 bits. A imagem tem 14.381.483.753 bytes e SHA-256 `e63abeaba270140b241817e9fc5b822f273d0d2da9884f093c67dda86ef9660c`. O runtime expõe `rom:` às consultas do SDK e o leitor VZIP recompilado usa o arquivo original. O trabalho do nxnative na atualização `0x20000` serviu de referência para as consultas de montagem. [Implementação de FS do nxnative](https://github.com/seedds/nxnative/blob/b2d46b86d03f4b03afe11ea61c67cdf00d7a5345/dm/host/hle_fs.c)

## Reproduzir

Prepare o ExeFS base e o ambiente de compilação conforme o [README](../README.md) e a [Fase 1](FASE-1.md). Execute na raiz do projeto. A imagem RomFS usa aproximadamente 13,4 GiB em disco. Se ela já foi criada pela ferramenta, comece pelo build.

```powershell
$py = '.\.venv\Scripts\python.exe'
$dump = 'E:\Switch 2 Games\Star Fox [0400E88025B1A000].nup'
& $py .\tools\dump.py $dump --pack-romfs
& $py .\tools\phase1.py build --jobs 12

$env:PATH = 'C:\msys64\ucrt64\bin;' + $env:PATH
$env:TOTK_GPU = 'null'
$env:TOTK_INPUT = 'none'
$env:TOTK_TRACE = 'fs'
& .\build\phase1-base\starfox.exe --selftest
& .\build\phase1-base\starfox.exe --boot *> .\build\phase2-boot.log
$bootExit = $LASTEXITCODE
Get-Content .\build\phase2-boot.log -Tail 20
$bootExit
```

`--boot` precisa registrar `VZIP data.zip header read`, `first NVN call` e `boot: passed`. Para recalcular o SHA-256 da imagem durante a execução, defina `$env:TOTK_ROMFS_VERIFY = 'force'` antes de `--boot` e confira `RomFS: image SHA-256 ok` no log.

O marco termina no bootstrap gráfico, antes da criação do dispositivo e do primeiro quadro. A [Fase 3](FASE-3.md) continua até os envios NVN repetidos com o backend nulo. A validação de TLS desta fase cobre a instalação do resolvedor durante o boot. Os testes de acesso ao armazenamento TLS por threads distintas seguem em aberto.
