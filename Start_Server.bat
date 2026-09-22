@echo off
chcp 65001 >nul
title Second Screen Server Controller
cd /d "%~dp0server"

:: Check if python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Khong tim thay Python tren he thong. Vui long cai dat Python 3.10+
    pause
    exit /b 1
)

:: Run the interactive CLI
python cli.py
