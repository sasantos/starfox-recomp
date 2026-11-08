@echo off
title Star Fox Remake (Nintendo Switch 2 PC Recompilation)
set "PATH=C:\msys64\ucrt64\bin;%PATH%"
set "TOTK_INPUT_SCRIPT="
set "TOTK_XLATE=%~dp0build\phase1-base\totk_xlate.exe"
set "TOTK_ROMFS=%~dp0build\extracted\base-00000000\romfs"
cd /d "%~dp0build\phase1-base"
echo ========================================================
echo   Star Fox Remake (Nintendo Switch 2) - PC Recompilation
echo ========================================================
echo   Controles:
echo     - Gamepad: DualSense, Xbox ou Pro Controller
echo     - Teclado:
echo         WASD : Mover Arwing
echo         E    : Confirmar / Tiro (Botao A)
echo         Shift: Freio / Cancelar (Botao B)
echo         Espaco: Botao X
echo         Tab  : Menu do Jogo / Pausar (Botao Plus)
echo         F1 / Esc: Menu de Configuracoes do Port
echo         F10  : Mostrar / Alternar Overlay de FPS
echo         F11  : Tela Cheia (Fullscreen)
echo ========================================================
starfox.exe --profile "..\phase1-profile"
pause
