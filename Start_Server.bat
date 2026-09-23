@echo off
chcp 65001 >nul
title Second Screen Server Controller
cd /d "%~dp0server"

:: Set link mode for uv if used
set UV_LINK_MODE=copy

:: 1. Uu tien chay tu virtual environment cua uv (.venv) neu da ton tai
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" cli.py %*
    goto :EOF
)

:: 2. Kiem tra neu co uv duoc cai dat
where uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    uv run cli.py %*
    goto :EOF
)

:: 3. Fallback sang python he thong
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python cli.py %*
    goto :EOF
)

echo.
echo ===================================================================
echo [!] Khong tim thay moi truong Python hoac uv tren he thong!
echo [*] Vui long chay file 'setup_server_uv.bat' o thu muc goc de tu dong cai dat.
echo ===================================================================
echo.
pause
exit /b 1
