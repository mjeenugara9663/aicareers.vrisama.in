@echo off
setlocal
cd /d "%~dp0"
title Vrisama Fashion PDF Studio
where py >nul 2>nul
if not errorlevel 1 (set "PY=py -3") else (set "PY=python")
%PY% --version >nul 2>nul
if errorlevel 1 (
 echo Please install Python 3.10+ from https://python.org/downloads/ and add to PATH.
 pause
 exit /b 1
)
if not exist app.py (
 curl.exe --fail --location -o app.py "https://aicareers.vrisama.in/fashion-pdf-studio/app.py"
 if errorlevel 1 (
  echo Could not download the application. Check internet connection.
  pause
  exit /b 1
 )
)
%PY% -m pip install --disable-pip-version-check "playwright>=1.45,<2" "pypdf>=5,<8"
if errorlevel 1 (
 echo Python dependencies could not be installed.
 pause
 exit /b 1
)
%PY% app.py
if errorlevel 1 (
 echo If a browser is missing, try: %PY% -m playwright install chromium
 pause
)
endlocal
