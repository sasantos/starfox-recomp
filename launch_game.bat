@echo off
title Star Fox Remake (Nintendo Switch 2 PC Recompilation)
cd /d "%~dp0build\phase1-base"
set TOTK_INPUT_SCRIPT=..\test_input.txt
echo ========================================================
echo   Star Fox Remake (Nintendo Switch 2) - PC Recompilation
echo ========================================================
echo   Controles:
echo     - Gamepad: DualSense (detectado), Xbox ou Pro Controller
echo     - Teclado:
echo         WASD : Mover Arwing
echo         E    : Confirmar / Tiro (Botao A)
echo         Shift: Freio / Cancelar (Botao B)
echo         Espaco: Botao X
echo         Tab  : Menu / Pausar / Pular (Botao Plus)
echo         Q / R: Manobras / Rolar (Botoes L / R)
echo ========================================================
starfox.exe --profile "..\phase1-profile"
pause
