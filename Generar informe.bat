@echo off
set PYTHONUTF8=1
cd /d "%~dp0"
echo Carpeta: %CD%

set PY=
py --version >/dev/null 2>/dev/null && set PY=py
if not defined PY if exist "%WINDIR%\py.exe" set PY="%WINDIR%\py.exe"
if not defined PY python --version >/dev/null 2>/dev/null && set PY=python
if not defined PY (
  echo No encuentro Python. Instalalo desde python.org y marca "Add python.exe to PATH".
  pause
  exit /b 1
)
echo Usando Python: %PY%

%PY% -c "import pypdf" 2>/dev/null || %PY% -m pip install pypdf

%PY% scripts\informe_windows.py %*
echo.
pause
