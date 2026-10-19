@echo off
set PYTHONUTF8=1
cd /d "%~dp0"
echo Carpeta: %CD%

set PY=
py --version >nul 2>nul && set PY=py
if not defined PY python --version >nul 2>nul && set PY=python
if not defined PY if exist "%WINDIR%\py.exe" set PY="%WINDIR%\py.exe"
rem Buscar Python aunque no se haya marcado "Add python.exe to PATH"
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set PY="%%D\python.exe"
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%D\python.exe" set PY="%%D\python.exe"
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-3*") do if exist "%%D\python.exe" set PY="%%D\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Python\bin\python.exe" set PY="%LOCALAPPDATA%\Python\bin\python.exe"
if not defined PY (
  echo No encuentro Python en esta PC.
  echo Instalalo desde python.org: "Windows installer (64-bit)" y marca "Add python.exe to PATH".
  pause
  exit /b 1
)
echo Usando Python: %PY%

%PY% -c "import pypdf" 2>nul || %PY% -m pip install pypdf

%PY% scripts\informe_windows.py %*
echo.
pause
