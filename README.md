# Star Fox Recomp

Projeto experimental para recompilar estaticamente o Star Fox de Nintendo Switch 2 (`0400E88025B1A000`) e rodá-lo no Windows x64. O primeiro alvo é a campanha solo offline do pacote base, com renderização Vulkan. Na Fase 3, o jogo carrega recursos do dump e executa envios NVN e apresentações consecutivas no backend nulo.

- [Plano por fases](docs/PLANO.md) com entregáveis, critérios de saída e revisões das referências.
- [Diagnóstico inicial](docs/FASE-0.md) com o que foi medido no dump e os pontos de integração já identificados.
- [Build da Fase 1](docs/FASE-1.md) com os comandos para gerar e compilar e os resultados dos testes da CPU.
- [Boot da Fase 2](docs/FASE-2.md) com os comandos de reprodução, os checkpoints observados e os limites do runtime offline.
- [Diagnóstico NVN da Fase 3](docs/FASE-3.md) com o trace do loop gráfico e os comandos para reproduzi-lo.

## Reproduzir a Fase 0

Execute os comandos na raiz do projeto usando PowerShell, Git e Python 3.12 de 64 bits.

```powershell
$dump = 'E:\Switch 2 Games\Star Fox [0400E88025B1A000].nup'
python -m venv .venv
$py = '.\.venv\Scripts\python.exe'
& $py -m pip install -r .\tools\requirements.txt

# Estrutura do NUP e SHA-256 de cada entrada. Lê cerca de 30 GB.
& $py -m nup.cli verify $dump

# Inventário JSON da tabela de conteúdo, sem extrair o RomFS.
New-Item -ItemType Directory -Path .\build -Force | Out-Null
& $py .\tools\dump.py $dump | Set-Content -Encoding utf8 .\build\inventario.json

# Executáveis do pacote base, com SHA-256 conferido na extração.
& $py .\tools\dump.py $dump --extract-exefs base
```

O ExeFS base está em `build/extracted/base-00000000/exefs`. O ExeFS da atualização pode ser extraído com `--extract-exefs update` e fica em `build/extracted/update-00020000/exefs`. A ferramenta recusa uma pasta de saída já existente. Os dois ExeFS somam cerca de 300 MB. A imagem RomFS usada no boot é preparada na Fase 2.

O Git ignora os diretórios `build/`, `generated/`, `local/` e `refs/`. Mantenha neles o conteúdo extraído, os logs detalhados, o C gerado e os futuros binários compilados do jogo. O port deverá compilar localmente a partir do dump de cada usuário.
