@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
title OpoRadar (PC)

rem --- Buscar Python ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo No encuentro Python. Instalalo desde https://www.python.org/downloads/
  echo marcando "Add python.exe to PATH" y vuelve a abrir este archivo.
  pause
  exit /b 1
)

if not exist config.json copy config.example.json config.json >nul

rem --- Solo la primera vez: pypdf (leer los PDF del BOC) y truststore/certifi (certificados de BOPA y BOPV) ---
%PY% -c "import pypdf, truststore, certifi" 2>nul || (
  echo Instalando complementos ^(pypdf, truststore, certifi^)...
  %PY% -m pip install --quiet --disable-pip-version-check pypdf truststore certifi
)

rem --- Puerto libre a partir del 8795 (el 8790 lo tienes ocupado en el PC) ---
for /f %%P in ('%PY% run.py puerto-libre 8795') do set OPORADAR_PUERTO=%%P
if not defined OPORADAR_PUERTO set OPORADAR_PUERTO=8795

echo.
echo  ===== OpoRadar en el PC =====
echo   1) Barrida real de BOE, BOC, BOPA, BOCYL y BOPV (ultimos 7 dias) y abrir la web
echo   2) Solo datos de ejemplo, para ver la interfaz al momento
echo   3) Abrir la web con lo que ya haya guardado
echo   4) Probar los lectores de los 5 boletines (no guarda nada, solo muestra lo que ve)
echo.
set /p OP="Elige 1, 2, 3 o 4 [1]: "
if "%OP%"=="" set OP=1

if "%OP%"=="4" (
  %PY% run.py probar
  echo.
  pause
  exit /b 0
)
if "%OP%"=="2" (
  %PY% run.py demo
)
if "%OP%"=="1" (
  echo.
  echo Revisando boletines, tarda unos 3-6 minutos la primera vez...
  %PY% run.py barrida --dias 7
)

echo.
echo Abriendo http://localhost:%OPORADAR_PUERTO%  (cierra esta ventana para parar el servidor)
start "" cmd /c "timeout /t 3 >nul & start http://localhost:%OPORADAR_PUERTO%"
%PY% run.py servir
pause
